"""Stage 2 — extract: (text, doc_type) -> ExtractedFact[].

No LLM for now. When ``demo`` is set we return the canned fixture facts; live we
parse the (OCR'd/pasted) text for **form fields** — the whole label→value pair, the
question *and* the answer — not just bare values. Two structures are recognised:

- markdown table rows (``| Tenancy commenced | 1 March 2021 |``), and
- colon-delimited label lines (``Date of this notice: 21 June 2026``).

A field whose answer is **blank** — an empty table cell (``| Signature | |``), a
label with nothing after the colon (``Signature:``), or a fill-in placeholder
(``Date: ______``) — is still emitted, with ``value=""``, so a downstream check or
the UI can flag the form as incomplete (e.g. an unsigned notice).

Values that appear in running prose rather than a labelled field (dates, € amounts)
are still captured as a fallback. Every fact carries a ``span`` that is a verbatim
substring of the source — the integrity check for the "receipt" — so a fact can
never cite text that wasn't there. For a labelled field the ``span`` is the whole
source line, so it holds the question alongside the answer.

Swap in a real model later for richer field understanding, claims, and parties.
"""

import re

from app.pipeline.util import load_fixture
from app.schemas import ExtractedFact

_MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|November|December"
)
_DATE_PATTERNS = [
    re.compile(rf"\b\d{{1,2}}\s+(?:{_MONTHS})\s+\d{{4}}\b", re.IGNORECASE),  # 1 March 2021
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),  # 2026-07-05
    re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"),  # 21/06/2026
]
_AMOUNT_PATTERN = re.compile(r"(?:€|EUR\s?)\s?\d[\d,]*(?:\.\d{2})?", re.IGNORECASE)

# A markdown table separator cell: dashes with optional alignment colons (---, :--:).
_SEPARATOR_CELL = re.compile(r"^:?-+:?$")
# A colon-delimited field label: starts the line, reasonably short, no interior
# sentence punctuation — so a prose sentence that merely contains a colon isn't
# mistaken for a field. Value is whatever follows the first colon.
_LABEL = r"[A-Za-z][A-Za-z0-9 ./()#'&-]{1,40}?"
_COLON_FIELD = re.compile(rf"^\s*({_LABEL})\s*:\s+(\S.*)$")
# Same, but with nothing (or only whitespace) after the colon — a blank field.
_COLON_BLANK = re.compile(rf"^\s*({_LABEL})\s*:\s*$")
# Markdown emphasis wrappers to peel off a value: **bold**, _italic_, *italic*.
_EMPHASIS = re.compile(r"^[*_]{1,2}(.*?)[*_]{1,2}$")
# Fill-in placeholder / "no answer" markers: a value made only of these counts as
# blank (e.g. "______", "......", "—", "-", "N/A").
_BLANK_VALUE = re.compile(r"^(?:[\s_.·—–/-]*|n/?a)$", re.IGNORECASE)


def _slug(label: str) -> str:
    """``"Tenancy commenced"`` -> ``"tenancy_commenced"`` for use as a fact key."""
    slug = re.sub(r"[^a-z0-9]+", "_", label.strip().lower()).strip("_")
    return slug or "field"


def _is_blank_value(value: str) -> bool:
    """True when a field's answer is absent — empty, a placeholder line, or N/A."""
    return bool(_BLANK_VALUE.match(value.strip()))


def _clean_value(value: str) -> str:
    value = value.strip()
    m = _EMPHASIS.match(value)
    if m and m.group(1).strip():
        value = m.group(1).strip()
    return value


def _split_table_row(line: str) -> list[str] | None:
    """Cells of a ``| a | b |`` markdown row, or None if the line isn't one."""
    stripped = line.strip()
    if "|" not in stripped:
        return None
    # Drop the leading/trailing pipe so we don't get empty edge cells.
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [c.strip() for c in stripped.split("|")]


def _is_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(_SEPARATOR_CELL.match(c) for c in cells if c != "")


def _regex_extract(text: str) -> list[ExtractedFact]:
    facts: list[ExtractedFact] = []
    key_counts: dict[str, int] = {}
    labelled_lines: set[str] = set()  # raw lines already emitted as a field pair

    def add(base_key: str, value: str, span: str, *, allow_empty: bool = False) -> None:
        value = value.strip()
        span = span.strip()
        if not span or span not in text:
            return
        if not value and not allow_empty:
            return
        key_counts[base_key] = key_counts.get(base_key, 0) + 1
        n = key_counts[base_key]
        key = base_key if n == 1 else f"{base_key}_{n}"
        facts.append(ExtractedFact(key=key, value=value, span=span))

    def add_field(label: str, value: str, span: str) -> None:
        """Emit a labelled field; a blank/placeholder answer becomes ``value=""``."""
        label = label.strip()
        if not label:
            return
        value = _clean_value(value)
        if _is_blank_value(value):
            add(_slug(label), "", span, allow_empty=True)
        else:
            add(_slug(label), value, span)
        labelled_lines.add(span.strip())

    lines = text.split("\n")
    for i, raw in enumerate(lines):
        cells = _split_table_row(raw)
        if cells is not None and len(cells) >= 2 and cells[0]:
            if _is_separator_row(cells):
                continue
            # A header row is the one immediately followed by a separator row.
            next_cells = _split_table_row(lines[i + 1]) if i + 1 < len(lines) else None
            if next_cells is not None and _is_separator_row(next_cells):
                continue
            add_field(cells[0], " ".join(cells[1:]).strip(), raw)
            continue

        m = _COLON_FIELD.match(raw)
        if m:
            add_field(m.group(1), m.group(2), raw)
            continue

        m = _COLON_BLANK.match(raw)
        if m:
            add_field(m.group(1), "", raw)

    # Fallback: dates and € amounts sitting in prose rather than a labelled field.
    # Span is the whole containing line so even these carry their surrounding context.
    for raw in lines:
        if raw.strip() in labelled_lines:
            continue
        for pat in _DATE_PATTERNS:
            for match in pat.finditer(raw):
                add("date", match.group(0), raw)
        for match in _AMOUNT_PATTERN.finditer(raw):
            add("amount", match.group(0), raw)

    return facts


def _fixture_facts(text: str) -> list[ExtractedFact]:
    try:
        parsed = load_fixture("extract_rtb_notice")
    except Exception:
        return []

    facts: list[ExtractedFact] = []
    for item in parsed.get("facts", []):
        key = (item.get("key") or "").strip()
        value = (item.get("value") or "").strip()
        span = item.get("span")
        if not key or not value:
            continue
        # Integrity: a span must be verbatim from the source, else drop it to None.
        if span is not None and span not in text:
            span = None
        facts.append(ExtractedFact(key=key, value=value, span=span))
    return facts


def extract_facts(text: str, doc_type: str, demo: bool = False) -> list[ExtractedFact]:
    if demo:
        return _fixture_facts(text)
    return _regex_extract(text)
