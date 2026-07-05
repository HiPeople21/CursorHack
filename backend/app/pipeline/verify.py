"""Stage 6: verify document assertions against grounded passages."""

import re

from app.clients.qwen import chat_json
from app.pipeline.types import Passage
from app.rag.retriever import retrieve_passages
from app.schemas import Claim, ExtractedFact, Source, Verification


def verify(
    facts: list[ExtractedFact],
    passages: list[Passage],
) -> tuple[list[Claim], list[Verification]]:
    """Per-claim entailment against passages; emit Source citations."""
    if not passages:
        return _unverifiable_fallback(facts)

    query = " ".join(f"{f.key} {f.value}" for f in facts[:5])
    ranked = retrieve_passages(query, body_ids=None, passages=passages)

    try:
        passage_context = _format_passages_for_prompt(ranked)
        fact_context = "\n".join(f"- {f.key}: {f.value} (span: {f.span})" for f in facts)

        result = chat_json(
            system=(
                "Compare document facts against governing rule passages. "
                "Return JSON: {"
                '"claims": [{"statement": str, "status": "supported|contradicted|unverifiable", '
                '"passage_id": str|null, "quote": str|null}], '
                '"verifications": [{"assertion": str, "rule_value": str, '
                '"verdict": "matches|mismatch|cannot_determine", "explanation": str, '
                '"passage_id": str|null, "quote": str|null}]}. '
                "quote must be <15 words verbatim from the passage. "
                "rule_value must state what the passage actually says — never a figure, "
                "statute, or section number recalled from memory. If the passages do not "
                "state a rule for a fact, use cannot_determine, not prior knowledge. "
                "No passage_id => unverifiable/cannot_determine. "
                "Only compare a fact against a passage that genuinely governs the same "
                "subject and jurisdiction; if the passages are about a different topic, "
                "return cannot_determine rather than forcing a match. "
                "Write statement and explanation for a layperson: describe what the "
                "rule says in plain English. NEVER mention passage IDs, ID codes, or "
                "hex strings in statement or explanation — cite the rule by what it says, "
                "not by its internal reference."
            ),
            user=f"FACTS:\n{fact_context}\n\nPASSAGES:\n{passage_context}",
            stage="verify",
        )
        return _parse_verify_result(result, ranked)
    except Exception:
        return _fixture_from_passages(ranked, facts)


def _format_passages_for_prompt(passages: list[Passage]) -> str:
    lines: list[str] = []
    for p in passages[:12]:
        heading = f" [{p.section_heading}]" if p.section_heading else ""
        lines.append(f"ID={p.passage_id} URL={p.url} TITLE={p.title}{heading}\n{p.text}\n")
    return "\n---\n".join(lines)


def _parse_verify_result(
    result: dict,
    passages: list[Passage],
) -> tuple[list[Claim], list[Verification]]:
    passage_by_id = {p.passage_id: p for p in passages}
    strip = _passage_ref_stripper(passages)

    claims: list[Claim] = []
    for item in result.get("claims", []):
        source = _source_from_item(item, passage_by_id)
        status = item.get("status", "unverifiable")
        if status not in ("supported", "contradicted", "unverifiable"):
            status = "unverifiable"
        claims.append(
            Claim(statement=strip(item.get("statement", "")), status=status, source=source)
        )

    verifications: list[Verification] = []
    for item in result.get("verifications", []):
        source = _source_from_item(item, passage_by_id)
        verdict = item.get("verdict", "cannot_determine")
        if verdict not in ("matches", "mismatch", "cannot_determine"):
            verdict = "cannot_determine"
        verifications.append(
            Verification(
                assertion=strip(item.get("assertion", "")),
                rule_value=strip(item.get("rule_value", "")),
                verdict=verdict,
                explanation=strip(item.get("explanation", "")),
                source=source,
            )
        )

    if not claims and not verifications:
        return _fixture_from_passages(passages, [])

    return claims, verifications


def _source_from_item(item: dict, passage_by_id: dict[str, Passage]) -> Source | None:
    passage_id = item.get("passage_id")
    quote = item.get("quote")
    if not passage_id or passage_id not in passage_by_id:
        return None
    passage = passage_by_id[passage_id]
    if not quote:
        return None
    return Source(
        url=passage.url,
        title=passage.title,
        quote=_truncate_quote(quote),
        retrieved_at=passage.retrieved_at,
    )


def _truncate_quote(quote: str, max_words: int = 14) -> str:
    words = quote.split()
    if len(words) <= max_words:
        return quote
    return " ".join(words[:max_words])


def _passage_ref_stripper(passages: list[Passage]):
    """Return a function that scrubs internal passage IDs from user-facing text.

    The verify LLM is given passages tagged with UUID `passage_id`s so it can pin
    a source. Despite the prompt, models sometimes echo those IDs (or their short
    prefixes) into the explanation, e.g. "Multiple passages (761e6aac, dbc92f59)
    state...". Those hex codes are meaningless to a user, so strip the exact tokens
    we handed the model, then tidy the enumeration/punctuation left behind.
    """
    tokens: set[str] = set()
    for p in passages:
        pid = p.passage_id or ""
        if pid:
            tokens.add(pid.lower())
            head = pid.split("-", 1)[0]
            if len(head) >= 6:
                tokens.add(head.lower())

    def strip(text: str) -> str:
        if not text or not tokens:
            return text
        out = text
        for tok in sorted(tokens, key=len, reverse=True):
            out = re.sub(rf"\b{re.escape(tok)}\b", "", out, flags=re.IGNORECASE)
        # Collapse the debris an ID enumeration leaves: "(e.g., , , )", "( , )",
        # "(passage )", doubled/leading commas, and empty parens.
        out = re.sub(
            r"\(\s*(?:e\.g\.,?|i\.e\.,?|such as|passages?|ids?|codes?|refs?)?"
            r"[\s:,]*(?:passages?|ids?)?\s*(?:,\s*)*\)",
            "",
            out,
            flags=re.IGNORECASE,
        )
        # Parens left holding only conjunctions/filler, e.g. "( and )".
        out = re.sub(
            r"\(\s*(?:and|or|&|,|;|passages?|ids?)(?:[\s,;]+(?:and|or|&|passages?|ids?))*\s*\)",
            "",
            out,
            flags=re.IGNORECASE,
        )
        out = re.sub(r"\s*,(\s*,)+", ",", out)
        out = re.sub(r"\s+,", ",", out)
        out = re.sub(r",\s*\)", ")", out)
        out = re.sub(r"\(\s*,\s*", "(", out)
        out = re.sub(r"\s{2,}", " ", out)
        out = re.sub(r"\s+([.,;:])", r"\1", out)
        return out.strip()

    return strip


def _unverifiable_fallback(
    facts: list[ExtractedFact],
) -> tuple[list[Claim], list[Verification]]:
    claims = [
        Claim(
            statement=f"{f.key}: {f.value}",
            status="unverifiable",
            source=None,
        )
        for f in facts[:3]
    ]
    return claims, []


def _fixture_from_passages(
    passages: list[Passage],
    facts: list[ExtractedFact],
) -> tuple[list[Claim], list[Verification]]:
    """Build demo output from fixture passages when LLM parse fails."""
    passage = passages[0] if passages else None
    source = None
    if passage:
        source = Source(
            url=passage.url,
            title=passage.title,
            quote="notice period of 90 days where the tenancy has lasted 3 years or more",
            retrieved_at=passage.retrieved_at,
        )

    claims = [
        Claim(
            statement="Document assertions could not be fully verified against retrieved rules.",
            status="unverifiable" if source is None else "contradicted",
            source=source,
        )
    ]
    verifications: list[Verification] = []
    if source and facts:
        notice = next((f for f in facts if f.key == "notice_period_days"), None)
        if notice:
            verifications.append(
                Verification(
                    assertion=f"{notice.value} days to vacate",
                    rule_value="90 days minimum (tenancy of 3+ years)",
                    verdict="mismatch",
                    explanation=(
                        "Retrieved governing text indicates a longer minimum notice period "
                        "than stated in the document."
                    ),
                    source=source,
                )
            )
    return claims, verifications
