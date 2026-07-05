"""Stage 0 — ingest: turn an uploaded image/PDF into layout-preserving text.

A user uploads a photo, screenshot, or PDF of an official document. We render
it to page image(s) and run **Tesseract OCR** locally, reconstructing the text
so relative layout survives — reading order, page boundaries, and rough column
alignment (so tables stay legible as aligned monospace text). That text becomes
the canonical ``text`` the rest of the frozen pipeline consumes, so positional
knowledge is carried in the text itself (no schema change needed).

OCR engine note: this uses Tesseract "for now" (no LLM anywhere in the pipeline
yet). Tesseract does not classify the document, so ``doc_type`` is left to the
downstream classify stage; ``IngestResult.doc_type`` is only populated on the
demo fixture path.

Behaviour:
- demo=True → return the canned ``fixtures/ingest_rtb_notice.json`` markdown so
  the money demo is bulletproof and stays consistent with the extract fixture
  spans (no Tesseract binary required for the demo).
- demo=False → real Tesseract OCR. Resilient: if OCR yields nothing, fall back
  to PyMuPDF's embedded text for digital PDFs so we still return *something*.
"""

import io
import re
from dataclasses import dataclass

from app.pipeline.util import load_fixture

# Guardrails / OCR tuning.
MAX_PAGES = 15
OCR_DPI = 300  # Tesseract likes ~300 DPI for rendered PDF pages.
PAGE_SEP = "--- Page {n} ---"
# A word gap wider than this many "characters" is treated as a real column gap
# (multiple spaces) rather than a normal inter-word space (single space).
COLUMN_GAP_CHARS = 1.6

# Tesseract reliably misreads the € glyph as one of these; restore it when it
# sits directly before a currency-shaped number (thousands-separated or with
# cents). The euro sign IS on the page — this recovers fidelity, not invents it.
_EURO_MISREAD_RE = re.compile(
    r"(?<![\w€])[-eEC©¢](\s?)(\d{1,3}(?:,\d{3})+(?:\.\d{2})?|\d+\.\d{2})"
)
_BLANK_RUN_RE = re.compile(r"\n{3,}")


@dataclass
class IngestResult:
    full_text_markdown: str
    pages: list[str]
    doc_type: str | None  # only set on the fixture path; else the classify stage decides
    jurisdiction: str
    page_count: int


def _is_pdf(data: bytes, content_type: str, filename: str) -> bool:
    return (
        data[:5] == b"%PDF-"
        or (content_type or "").lower() == "application/pdf"
        or filename.lower().endswith(".pdf")
    )


def _join_pages(page_texts: list[str]) -> str:
    if len(page_texts) == 1:
        return page_texts[0]
    parts: list[str] = []
    for i, text in enumerate(page_texts, start=1):
        parts.append(PAGE_SEP.format(n=i))
        parts.append(text)
    return "\n\n".join(parts)


def _load_fixture_ingest() -> IngestResult:
    """Demo path: canned layout markdown for the defective RTB notice."""
    parsed = load_fixture("ingest_rtb_notice")
    page_objs = sorted(parsed.get("pages", []), key=lambda p: p.get("page", 0))
    pages = [p.get("markdown", "").strip() for p in page_objs if p.get("markdown")]
    return IngestResult(
        full_text_markdown=_join_pages(pages),
        pages=pages,
        doc_type=parsed.get("doc_type"),
        jurisdiction=parsed.get("jurisdiction", "IE"),
        page_count=len(pages),
    )


def _pdf_to_images(data: bytes) -> tuple[list["Image.Image"], list[str]]:  # noqa: F821
    """Render up to MAX_PAGES pages to PIL images. Also return embedded text per page."""
    import fitz  # PyMuPDF
    from PIL import Image

    images: list[Image.Image] = []
    embedded_text: list[str] = []
    zoom = OCR_DPI / 72
    matrix = fitz.Matrix(zoom, zoom)
    with fitz.open(stream=data, filetype="pdf") as doc:
        for page in doc[:MAX_PAGES]:
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            images.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
            embedded_text.append(page.get_text().strip())
    return images, embedded_text


def _clean_ocr_text(text: str) -> str:
    """Repair common Tesseract artifacts without altering real content."""
    text = _EURO_MISREAD_RE.sub(lambda m: "€" + m.group(1) + m.group(2), text)
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    text = _BLANK_RUN_RE.sub("\n\n", text)  # collapse runs of blank lines
    return text.strip()


def _reconstruct_line(words: list[tuple[int, int, str]], char_w: float, page_left: int) -> str:
    """Rebuild one line from word boxes (left, right, text), already sorted by left.

    Uses a *single* space for ordinary word gaps and only widens to multiple
    spaces for genuine column gaps, so prose stays clean while tables keep their
    columns. Leading indentation is measured relative to the page's left margin,
    so the body isn't pushed right by a global offset."""
    indent_cols = int(round((words[0][0] - page_left) / char_w)) if char_w > 0 else 0
    line = " " * max(indent_cols, 0)
    prev_right: int | None = None
    for left, right, text in words:
        if prev_right is not None:
            gap_cols = (left - prev_right) / char_w if char_w > 0 else 0
            line += " " * int(round(gap_cols)) if gap_cols >= COLUMN_GAP_CHARS else " "
        line += text
        prev_right = right
    return line


def _ocr_image(img: "Image.Image") -> str:  # noqa: F821
    """Layout-preserving OCR: group words into lines by their block/paragraph/line,
    keep reading order, and preserve horizontal spacing via bounding boxes."""
    import pytesseract
    from pytesseract import Output

    data = pytesseract.image_to_data(img, output_type=Output.DICT)
    n = len(data["text"])

    words = []  # (block, par, line, left, right, text)
    for i in range(n):
        text = data["text"][i].strip()
        if not text:
            continue
        left, width = data["left"][i], data["width"][i]
        words.append(
            (data["block_num"][i], data["par_num"][i], data["line_num"][i], left, left + width, text)
        )
    if not words:
        return ""

    # Average glyph advance (px) — the unit for turning pixel gaps into columns.
    total_chars = sum(len(w[5]) for w in words)
    total_width = sum(w[4] - w[3] for w in words)
    char_w = (total_width / total_chars) if total_chars else 1.0
    page_left = min(w[3] for w in words)

    lines: dict[tuple[int, int, int], list[tuple[int, int, str]]] = {}
    for block, par, line_no, left, right, text in words:
        lines.setdefault((block, par, line_no), []).append((left, right, text))

    out_lines: list[str] = []
    prev_block: int | None = None
    for key in sorted(lines):
        block = key[0]
        if prev_block is not None and block != prev_block:
            out_lines.append("")  # blank line between blocks preserves vertical grouping
        line_words = sorted(lines[key], key=lambda w: w[0])
        out_lines.append(_reconstruct_line(line_words, char_w, page_left))
        prev_block = block

    return _clean_ocr_text("\n".join(out_lines))


def _fallback_from_text(embedded: list[str]) -> IngestResult | None:
    """Best-effort result from PyMuPDF embedded text when OCR yields nothing."""
    pages = [t for t in embedded if t]
    if not pages:
        return None
    return IngestResult(
        full_text_markdown=_join_pages(pages),
        pages=pages,
        doc_type=None,
        jurisdiction="IE",
        page_count=len(pages),
    )


def ingest_document(
    data: bytes, filename: str, content_type: str, demo: bool = False
) -> IngestResult:
    """Digitise an uploaded image/PDF into layout-preserving text via Tesseract OCR."""
    if demo:
        return _load_fixture_ingest()

    from PIL import Image

    embedded_text: list[str] = []
    if _is_pdf(data, content_type, filename):
        images, embedded_text = _pdf_to_images(data)
        if not images:
            raise ValueError("PDF contained no renderable pages")
    else:
        images = [Image.open(io.BytesIO(data)).convert("RGB")]

    try:
        page_texts = [t for t in (_ocr_image(img) for img in images) if t.strip()]
        if not page_texts:
            raise ValueError("OCR produced no text")
        return IngestResult(
            full_text_markdown=_join_pages(page_texts),
            pages=page_texts,
            doc_type=None,  # Tesseract doesn't classify — leave it to the classify stage
            jurisdiction="IE",
            page_count=len(page_texts),
        )
    except Exception:
        fallback = _fallback_from_text(embedded_text)
        if fallback is not None:
            return fallback
        raise
