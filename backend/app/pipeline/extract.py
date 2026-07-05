"""Stage 2: extract structured facts from the document."""

from app.clients.qwen import chat_json
from app.schemas import ExtractedFact


def extract(text: str, doc_type: str) -> tuple[list[ExtractedFact], str]:
    """Return extracted facts and a plain-language summary."""
    try:
        result = chat_json(
            system=(
                "Extract case-specific facts from this official document. "
                'Return JSON: {"facts": [{"key": str, "value": str, "span": str|null}], '
                '"plain_summary": str}. Keys like notice_period_days, amount_due, tenancy_start.'
            ),
            user=f"doc_type={doc_type}\n\n{text[:6000]}",
            stage="extract",
        )
        facts = [
            ExtractedFact(key=f["key"], value=f["value"], span=f.get("span"))
            for f in result.get("facts", [])
            if "key" in f and "value" in f
        ]
        summary = result.get("plain_summary", "Document received for analysis.")
        return facts, summary
    except Exception:
        return [], "Document received for analysis."
