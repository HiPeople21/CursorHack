"""Stage 1: classify(text) -> (doc_type, jurisdiction). One Qwen call.

Signature per CLAUDE.md: `classify(text) -> doc_type, jurisdiction`. We take
an optional `default_jurisdiction` (the jurisdiction hint from the request)
so the model has context and we always have a safe fallback if it returns
nothing usable.
"""

from __future__ import annotations

from app.clients import qwen

VALID_DOC_TYPES = {"tenancy", "insurance", "medical_bill", "gov_letter", "other"}

SYSTEM_PROMPT = """You classify official/bureaucratic documents for a legal-rights tool.
Respond with JSON only. No prose, no markdown, no explanation outside the JSON object.

Return exactly this JSON shape:
{"doc_type": "<one of: tenancy, insurance, medical_bill, gov_letter, other>", "jurisdiction": "<ISO country/region code, e.g. IE, US, UK>"}
"""


def classify(text: str, default_jurisdiction: str = "IE") -> tuple[str, str]:
    """Classify a document's type and jurisdiction.

    Never raises. Falls back to ("other", default_jurisdiction) if the model
    call fails or returns something unparseable/invalid.
    """
    user_prompt = (
        f"Jurisdiction hint from user: {default_jurisdiction}\n\n"
        f"Document text:\n{text[:6000]}"
    )

    data = qwen.chat_json(SYSTEM_PROMPT, user_prompt, mock_fixture="classify.json")

    doc_type = "other"
    jurisdiction = default_jurisdiction or "IE"

    if isinstance(data, dict):
        candidate_type = data.get("doc_type")
        if isinstance(candidate_type, str) and candidate_type.strip().lower() in VALID_DOC_TYPES:
            doc_type = candidate_type.strip().lower()

        candidate_jurisdiction = data.get("jurisdiction")
        if isinstance(candidate_jurisdiction, str) and candidate_jurisdiction.strip():
            jurisdiction = candidate_jurisdiction.strip()

    return doc_type, jurisdiction
