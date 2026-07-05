"""Stage 1: classify document type and jurisdiction."""

from typing import Literal

from app.clients.qwen import chat_json

DocType = Literal["tenancy", "insurance", "medical_bill", "gov_letter", "other"]


def classify(text: str, jurisdiction: str = "IE") -> tuple[DocType, str]:
    try:
        result = chat_json(
            system=(
                "Classify the official document. Return JSON only: "
                '{"doc_type": "tenancy|insurance|medical_bill|gov_letter|other", '
                '"jurisdiction": "IE"}'
            ),
            user=text[:4000],
            stage="classify",
        )
        doc_type = result.get("doc_type", "other")
        if doc_type not in ("tenancy", "insurance", "medical_bill", "gov_letter", "other"):
            doc_type = "other"
        return doc_type, result.get("jurisdiction", jurisdiction or "IE")
    except Exception:
        return _heuristic_classify(text, jurisdiction)


def _heuristic_classify(text: str, jurisdiction: str) -> tuple[DocType, str]:
    lowered = text.lower()
    if any(w in lowered for w in ("tenancy", "landlord", "rent", "rtb", "vacate")):
        return "tenancy", jurisdiction or "IE"
    if any(w in lowered for w in ("insurance", "policy", "premium", "claim")):
        return "insurance", jurisdiction or "IE"
    if any(w in lowered for w in ("hospital", "medical", "invoice", "treatment")):
        return "medical_bill", jurisdiction or "IE"
    if any(w in lowered for w in ("department", "minister", "revenue", "an post")):
        return "gov_letter", jurisdiction or "IE"
    return "other", jurisdiction or "IE"
