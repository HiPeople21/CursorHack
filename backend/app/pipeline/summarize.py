"""Small helper (not one of the six named stages) that produces the
`plain_summary` field on DecodeResult. It's a single, additional Qwen call
that piggybacks on the already-extracted facts, so `classify`/`extract` keep
exactly the signatures specified in CLAUDE.md.
"""

from __future__ import annotations

from app.clients import qwen
from app.schemas import ExtractedFact

SYSTEM_PROMPT = """You write a short, plain-English summary of an official/bureaucratic document
for someone who is not a lawyer. 2-4 sentences. Neutral, factual tone — do not give legal advice
or state legal conclusions, just explain what the document says and does.

Respond with JSON only, no prose, no markdown fences. Return exactly this shape:
{"plain_summary": "<2-4 sentence summary>"}
"""


def summarize(text: str, doc_type: str, facts: list[ExtractedFact]) -> str:
    """Produce a plain-language summary of the document.

    Never raises. Falls back to a generic message if the model call fails.
    """
    facts_block = (
        "\n".join(f"- {f.key}: {f.value}" for f in facts) if facts else "(no facts extracted)"
    )
    user_prompt = (
        f"Document type: {doc_type}\n\nKey facts:\n{facts_block}\n\nDocument text:\n{text[:6000]}"
    )

    try:
        data = qwen.chat_json(SYSTEM_PROMPT, user_prompt, stage="summarize")
    except Exception:
        data = {}

    if isinstance(data, dict):
        summary = data.get("plain_summary")
        if isinstance(summary, str) and summary.strip():
            return summary.strip()

    return "We could not automatically generate a plain-language summary for this document."
