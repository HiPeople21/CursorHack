"""Stage 1: classify document type and jurisdiction."""

from typing import Literal

from app.clients.qwen import chat_json
from app.pipeline.jurisdiction import infer_jurisdiction_from_text, normalize_jurisdiction

DocType = Literal["tenancy", "insurance", "medical_bill", "gov_letter", "other"]


def classify(text: str, jurisdiction: str | None = None) -> tuple[DocType, str]:
    hint = (
        f" The caller suggested jurisdiction {normalize_jurisdiction(jurisdiction)}."
        if jurisdiction
        else ""
    )
    try:
        result = chat_json(
            system=(
                "Classify the official document. Detect jurisdiction as an ISO 3166-1 "
                f"alpha-2 country code from addresses, legal bodies, and statutes.{hint} "
                "Return JSON only: "
                '{"doc_type": "tenancy|insurance|medical_bill|gov_letter|other", '
                '"jurisdiction": "XX"}'
            ),
            user=text[:4000],
            stage="classify",
        )
        doc_type = result.get("doc_type", "other")
        if doc_type not in ("tenancy", "insurance", "medical_bill", "gov_letter", "other"):
            doc_type = "other"
        return doc_type, _resolve_jurisdiction(result.get("jurisdiction"), jurisdiction, text)
    except Exception:
        return _heuristic_classify(text, jurisdiction)


def _resolve_jurisdiction(
    detected: str | None,
    hint: str | None,
    text: str,
) -> str:
    if detected:
        normalized = normalize_jurisdiction(detected)
        if normalized:
            return normalized
    if hint:
        normalized = normalize_jurisdiction(hint)
        if normalized:
            return normalized
    inferred = infer_jurisdiction_from_text(text)
    if inferred:
        return inferred
    return "UNK"


def _heuristic_classify(text: str, jurisdiction: str | None) -> tuple[DocType, str]:
    place = _resolve_jurisdiction(None, jurisdiction, text)
    lowered = text.lower()
    if any(w in lowered for w in ("tenancy", "landlord", "rent", "rtb", "vacate")):
        return "tenancy", place
    if any(w in lowered for w in ("insurance", "policy", "premium", "claim")):
        return "insurance", place
    if any(w in lowered for w in ("hospital", "medical", "invoice", "treatment")):
        return "medical_bill", place
    if any(w in lowered for w in ("department", "minister", "revenue", "an post")):
        return "gov_letter", place
    return "other", place
