"""Government institution identification from document text.

Only returns a body when the document itself references that institution.
When nothing is found, the pipeline asks the user to supply the institution.
"""

import re

from app.pipeline.jurisdiction import infer_jurisdiction_from_text, normalize_jurisdiction
from app.pipeline.types import IdentifiedBody


def identify_bodies(
    text: str,
    doc_type: str,
    jurisdiction: str,
) -> list[IdentifiedBody]:
    """Identify government bodies explicitly referenced in the document text."""
    place = normalize_jurisdiction(jurisdiction) or infer_jurisdiction_from_text(text) or "UNK"
    lowered = text.lower()

    bodies = _identify_ie(lowered, text, place) + _identify_gb(lowered, text, place)
    seen: set[str] = set()
    unique: list[IdentifiedBody] = []
    for body in bodies:
        if body.body_id in seen:
            continue
        seen.add(body.body_id)
        unique.append(body)
    return unique


def _identify_ie(lowered: str, text: str, place: str) -> list[IdentifiedBody]:
    bodies: list[IdentifiedBody] = []

    if "residential tenancies board" in lowered or _has_word(lowered, "rtb"):
        span = _find_span(text, ["Residential Tenancies Board", "RTB"])
        bodies.append(
            IdentifiedBody(
                body_id="rtb",
                display_name="Residential Tenancies Board",
                confidence=0.9,
                jurisdiction=place,
                source_span=span,
                match_kind="explicit",
            )
        )

    if "citizens information" in lowered:
        bodies.append(
            IdentifiedBody(
                body_id="citizens_information",
                display_name="Citizens Information",
                confidence=0.9,
                jurisdiction=place,
                source_span=_find_span(text, ["Citizens Information"]),
                match_kind="explicit",
            )
        )

    if "revenue commissioners" in lowered or "revenue.ie" in lowered:
        bodies.append(
            IdentifiedBody(
                body_id="revenue",
                display_name="Revenue Commissioners",
                confidence=0.9,
                jurisdiction=place,
                source_span=_find_span(text, ["Revenue Commissioners", "revenue.ie"]),
                match_kind="explicit",
            )
        )

    return bodies


def _identify_gb(lowered: str, text: str, place: str) -> list[IdentifiedBody]:
    bodies: list[IdentifiedBody] = []

    if "tenancy deposit scheme" in lowered or _has_word(lowered, "tds"):
        span = _find_span(text, ["Tenancy Deposit Scheme", "TDS"])
        bodies.append(
            IdentifiedBody(
                body_id="tds",
                display_name="Tenancy Deposit Scheme",
                confidence=0.9,
                jurisdiction=place,
                source_span=span,
                match_kind="explicit",
            )
        )

    if "hmrc" in lowered or "hm revenue and customs" in lowered:
        bodies.append(
            IdentifiedBody(
                body_id="hmrc",
                display_name="HM Revenue and Customs",
                confidence=0.9,
                jurisdiction=place,
                source_span=_find_span(text, ["HMRC", "HM Revenue and Customs"]),
                match_kind="explicit",
            )
        )

    if "first-tier tribunal" in lowered or "housing act" in lowered:
        bodies.append(
            IdentifiedBody(
                body_id="tds",
                display_name="Tenancy Deposit Scheme",
                confidence=0.75,
                jurisdiction=place,
                source_span=_find_span(text, ["First-tier Tribunal", "Housing Act"]),
                match_kind="reference",
            )
        )

    return bodies


def _has_word(lowered: str, word: str) -> bool:
    return re.search(rf"\b{re.escape(word)}\b", lowered) is not None


def _find_span(text: str, needles: list[str]) -> str | None:
    for needle in needles:
        idx = text.lower().find(needle.lower())
        if idx >= 0:
            start = max(0, idx - 20)
            end = min(len(text), idx + len(needle) + 40)
            return text[start:end].strip()
    return None
