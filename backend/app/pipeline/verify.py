"""Stage 5: verify(facts, passages) -> (Claim[], Verification[]).

This is the defensible core of the whole product. For every assertion the
document makes, we ask Qwen to entail it against the grounded governing-rule
passages, but we NEVER trust the model's word for whether a citation is
real: every Claim/Verification the model proposes is independently checked
here — the "quote" it returns must be a genuine, near-verbatim substring of
the passage it claims to cite. If that check fails (or no passage was
proposed at all), we override the verdict/status to
"cannot_determine"/"unverifiable" and drop the source. No source is ever
fabricated; there is no code path that constructs a Source without a real,
verified grounded passage.
"""

from __future__ import annotations

import re

from app.schemas import Claim, ExtractedFact, Source, Verification
from app.clients import qwen

_MAX_QUOTE_WORDS = 15

SYSTEM_PROMPT = """You are a strict legal-document entailment checker.

You are given:
1. Facts extracted from a document a person received (e.g. a tenancy termination notice).
2. Numbered passages scraped from official governing-rule sources (statutes, government
   guidance pages) for the relevant jurisdiction.

Your job: for each assertion the document effectively makes (derived from the facts) that the
governing-rule passages can confirm or refute, produce a "verification" comparing what the
document asserts to what the passage says the rule actually is. Also produce "claims" — general
statements about the governing rule itself, each grounded in exactly one passage.

CRITICAL RULES:
- Only cite a passage if it truly, verbatim, supports the quote you give. The "quote" field MUST
  be an exact, contiguous substring (word-for-word, same spelling/punctuation) copied from the
  numbered passage you reference, under 15 words long.
- If you cannot find a passage that genuinely addresses an assertion, DO NOT invent one. Instead
  omit "passage_index" and "quote" (or set them to null) and set verdict/status to
  "cannot_determine" / "unverifiable".
- Never fabricate a citation. Never paraphrase text and present it as a quote.
- Respond with JSON only, no prose, no markdown fences. Return exactly this shape:

{
  "verifications": [
    {
      "assertion": "<what the document/notice claims, in plain terms>",
      "passage_index": <int index into the passages list, or null>,
      "quote": "<verbatim substring of that passage, <15 words, or null>",
      "rule_value": "<what the governing rule actually requires>",
      "verdict": "<matches | mismatch | cannot_determine>",
      "explanation": "<1-3 sentences, plain English>"
    }
  ],
  "claims": [
    {
      "statement": "<a general statement about the governing rule>",
      "passage_index": <int index into the passages list, or null>,
      "quote": "<verbatim substring of that passage, <15 words, or null>",
      "status": "<supported | contradicted | unverifiable>"
    }
  ]
}
"""


def _normalize(text: str) -> str:
    return " ".join(text.split()).lower()


def _truncate_quote(quote: str, max_words: int = _MAX_QUOTE_WORDS) -> str:
    words = quote.split()
    if len(words) <= max_words:
        return quote
    return " ".join(words[:max_words])


def _resolve_source(
    passages: list[dict[str, str]],
    passage_index: object,
    quote: object,
) -> Source | None:
    """Verify a proposed (passage_index, quote) pair and build a real Source.

    Returns None if the index is out of range, the quote is missing/empty,
    or the quote is not actually a verbatim substring of that passage's
    content. This is the enforcement point that stops the model from ever
    fabricating a citation.
    """
    if not isinstance(passage_index, int) or isinstance(passage_index, bool):
        return None
    if passage_index < 0 or passage_index >= len(passages):
        return None
    if not isinstance(quote, str) or not quote.strip():
        return None

    passage = passages[passage_index]
    quote = quote.strip()

    normalized_passage = _normalize(passage["content"])
    normalized_quote = _normalize(quote)
    if not normalized_quote or normalized_quote not in normalized_passage:
        return None

    quote = _truncate_quote(quote)

    return Source(
        url=passage["url"],
        title=passage["title"],
        quote=quote,
        retrieved_at=passage["retrieved_at"],
    )


def verify(
    doc_type: str,
    facts: list[ExtractedFact],
    passages: list[dict[str, str]],
) -> tuple[list[Claim], list[Verification]]:
    """Per-claim/per-assertion entailment against grounded governing-rule passages.

    Never raises. If there are no passages at all, returns no verifications
    and (optionally) unverifiable claims for the raw facts, since nothing can
    be grounded. Every returned Claim/Verification with a non-null source has
    been independently confirmed to quote real, verbatim passage text.
    """
    if not passages:
        return [], []

    facts_block = (
        "\n".join(f"- {f.key} = {f.value}" for f in facts) if facts else "(no facts extracted)"
    )
    passages_block = "\n\n".join(
        f"[{i}] (url={p['url']} | title={p['title']})\n{p['content']}"
        for i, p in enumerate(passages)
    )
    user_prompt = (
        f"Document type: {doc_type}\n\n"
        f"Extracted facts:\n{facts_block}\n\n"
        f"Governing-rule passages:\n{passages_block}"
    )

    data = qwen.chat_json(SYSTEM_PROMPT, user_prompt, mock_fixture="verify.json")

    verifications: list[Verification] = []
    claims: list[Claim] = []

    if not isinstance(data, dict):
        return claims, verifications

    raw_verifications = data.get("verifications")
    if isinstance(raw_verifications, list):
        for item in raw_verifications:
            if not isinstance(item, dict):
                continue
            assertion = item.get("assertion")
            if not isinstance(assertion, str) or not assertion.strip():
                continue

            source = _resolve_source(passages, item.get("passage_index"), item.get("quote"))
            verdict = item.get("verdict")
            explanation = item.get("explanation")
            explanation = explanation.strip() if isinstance(explanation, str) else ""
            rule_value = item.get("rule_value")
            rule_value = rule_value.strip() if isinstance(rule_value, str) and rule_value.strip() else "Not stated in retrieved source"

            if source is None:
                verdict = "cannot_determine"
                if not explanation:
                    explanation = (
                        "No governing-rule passage could be verified to support or "
                        "contradict this assertion."
                    )
            elif verdict not in ("matches", "mismatch", "cannot_determine"):
                verdict = "cannot_determine"

            verifications.append(
                Verification(
                    assertion=assertion.strip(),
                    rule_value=rule_value,
                    verdict=verdict,
                    explanation=explanation or "No explanation provided.",
                    source=source,
                )
            )

    raw_claims = data.get("claims")
    if isinstance(raw_claims, list):
        for item in raw_claims:
            if not isinstance(item, dict):
                continue
            statement = item.get("statement")
            if not isinstance(statement, str) or not statement.strip():
                continue

            source = _resolve_source(passages, item.get("passage_index"), item.get("quote"))
            status = item.get("status")

            if source is None:
                status = "unverifiable"
            elif status not in ("supported", "contradicted", "unverifiable"):
                status = "unverifiable"

            claims.append(
                Claim(
                    statement=statement.strip(),
                    status=status,
                    source=source,
                )
            )

    return claims, verifications
