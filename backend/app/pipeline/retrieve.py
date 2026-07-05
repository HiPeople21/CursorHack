"""Stage 3: retrieve(doc_type, facts, jurisdiction) -> candidate URLs.

Uses Exa neural search to find the governing-rule pages for this document
type and jurisdiction (e.g. "RTB notice period termination tenancy Ireland").
"""

from __future__ import annotations

from app.clients import exa
from app.schemas import ExtractedFact

_DOC_TYPE_QUERY_HINTS = {
    "tenancy": "residential tenancy termination notice period statutory minimum rules",
    "insurance": "insurance claim denial appeal rights regulations",
    "medical_bill": "medical billing dispute patient rights regulations",
    "gov_letter": "government notice appeal rights regulations",
    "other": "consumer rights official regulations",
}

_JURISDICTION_NAMES = {
    "IE": "Ireland",
    "UK": "United Kingdom",
    "US": "United States",
}


def _build_query(doc_type: str, facts: list[ExtractedFact], jurisdiction: str) -> str:
    hint = _DOC_TYPE_QUERY_HINTS.get(doc_type, _DOC_TYPE_QUERY_HINTS["other"])
    fact_terms = " ".join(f.key.replace("_", " ") for f in facts[:4])
    country = _JURISDICTION_NAMES.get(jurisdiction, jurisdiction)
    return f"{hint} {fact_terms} {country} official rules".strip()


def retrieve(
    doc_type: str,
    facts: list[ExtractedFact],
    jurisdiction: str,
) -> list[dict[str, str]]:
    """Find candidate governing-rule pages for this doc_type/jurisdiction.

    Returns a list of {"url": str, "title": str} dicts. Never raises —
    returns [] if search fails, so downstream stages ground against nothing
    and verify() naturally produces "unverifiable"/"cannot_determine".
    """
    query = _build_query(doc_type, facts, jurisdiction)
    return exa.search(query, num_results=5, mock_fixture="retrieve.json")
