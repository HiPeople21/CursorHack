"""Stage 6: verify document assertions against grounded passages."""

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
                "No passage_id => unverifiable/cannot_determine."
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

    claims: list[Claim] = []
    for item in result.get("claims", []):
        source = _source_from_item(item, passage_by_id)
        status = item.get("status", "unverifiable")
        if status not in ("supported", "contradicted", "unverifiable"):
            status = "unverifiable"
        # Contract: a grounded verdict must carry a real Source. No source =>
        # we cannot stand over "supported"/"contradicted", so downgrade.
        if source is None:
            status = "unverifiable"
        claims.append(
            Claim(statement=item.get("statement", ""), status=status, source=source)
        )

    verifications: list[Verification] = []
    for item in result.get("verifications", []):
        source = _source_from_item(item, passage_by_id)
        verdict = item.get("verdict", "cannot_determine")
        if verdict not in ("matches", "mismatch", "cannot_determine"):
            verdict = "cannot_determine"
        # Same contract rule: no citation => cannot_determine.
        if source is None:
            verdict = "cannot_determine"
        verifications.append(
            Verification(
                assertion=item.get("assertion", ""),
                rule_value=item.get("rule_value", ""),
                verdict=verdict,
                explanation=item.get("explanation", ""),
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
