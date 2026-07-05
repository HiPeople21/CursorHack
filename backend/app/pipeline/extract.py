"""Stage 2: extract(text, doc_type) -> ExtractedFact[].

Qwen returns structured JSON facts, each carrying the verbatim source span
it was pulled from. This is what makes the result case-specific rather than
a generic explainer.
"""

from __future__ import annotations

from app.clients import qwen
from app.schemas import ExtractedFact

SYSTEM_PROMPT = """You extract specific, structured facts from an official/bureaucratic document
(tenancy notice, insurance letter, medical bill, government letter, etc).

Respond with JSON only, no prose. Return exactly this shape:
{"facts": [{"key": "<short_snake_case_key>", "value": "<the extracted value as a string>", "span": "<the exact verbatim substring of the document text this came from, or null if not a direct quote>"}]}

Extract things like: dates, deadlines, amounts, notice periods, durations, names of parties,
case/reference numbers, and any other concrete figures the document states about this specific
case. Only include facts that are actually present in the text. Do not invent facts.
"""


def extract(text: str, doc_type: str) -> list[ExtractedFact]:
    """Extract structured, source-spanned facts from the document text.

    Never raises. Returns an empty list if the model call fails or returns
    nothing usable — the pipeline degrades gracefully rather than crashing.
    """
    user_prompt = f"Document type: {doc_type}\n\nDocument text:\n{text[:8000]}"

    data = qwen.chat_json(SYSTEM_PROMPT, user_prompt, mock_fixture="extract.json")

    facts: list[ExtractedFact] = []
    raw_facts = data.get("facts") if isinstance(data, dict) else None
    if not isinstance(raw_facts, list):
        return facts

    for item in raw_facts:
        if not isinstance(item, dict):
            continue
        key = item.get("key")
        value = item.get("value")
        if not isinstance(key, str) or not key.strip():
            continue
        if value is None:
            continue
        span = item.get("span")
        facts.append(
            ExtractedFact(
                key=key.strip(),
                value=str(value).strip(),
                span=span.strip() if isinstance(span, str) and span.strip() else None,
            )
        )

    return facts
