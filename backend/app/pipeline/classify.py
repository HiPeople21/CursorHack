"""Stage 1 — classify: (text) -> (doc_type, jurisdiction).

No LLM for now. When ``demo`` is set we return the canned fixture; live we use a
light keyword heuristic over the (OCR'd) text. Swap in a real model later.
"""

import re

from app.pipeline.util import load_fixture

DOC_TYPES = ("tenancy", "insurance", "medical_bill", "gov_letter", "other")

# Lowercase keyword cues per document type, checked in priority order.
_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("tenancy", ("tenancy", "landlord", "tenant", "termination of tenancy", "rtb", "residential tenancies", "notice of termination", "lease")),
    ("medical_bill", ("hospital", "patient", "invoice", "amount due", "medical", "consultant", "outpatient")),
    ("insurance", ("insurance", "policy", "premium", "insurer", "claim number", "cover")),
    ("gov_letter", ("revenue", "department of", "social welfare", "gov.ie", "pps number", "citizens information")),
]


def _cue_matches(cue: str, text: str) -> bool:
    """Whole-word (phrase) match so a cue can't fire on a substring —
    e.g. the tenancy cue "lease" must not match inside "please"."""
    return re.search(rf"\b{re.escape(cue)}\b", text) is not None


def _heuristic_doc_type(text: str) -> str:
    """Pick the doc_type with the most whole-word cue hits.

    Scoring (rather than first-match-wins) stops a single weak/ambiguous cue
    from outranking several strong ones — e.g. a lone "policy" in a footer must
    not beat "department of" + "social welfare" + "gov.ie". Ties fall back to the
    priority order in ``_KEYWORDS``.
    """
    low = text.lower()
    best_type = "other"
    best_score = 0
    for doc_type, cues in _KEYWORDS:
        score = sum(1 for cue in cues if _cue_matches(cue, low))
        if score > best_score:
            best_type, best_score = doc_type, score
    return best_type


def classify(text: str, demo: bool = False) -> tuple[str, str]:
    if demo:
        try:
            f = load_fixture("classify_rtb_notice")
            doc_type = f.get("doc_type", "other")
            if doc_type not in DOC_TYPES:
                doc_type = "other"
            return doc_type, f.get("jurisdiction") or "IE"
        except Exception:
            return "other", "IE"

    return _heuristic_doc_type(text), "IE"
