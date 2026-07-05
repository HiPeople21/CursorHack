"""Pipeline entry point.

Chains the six stages (classify -> extract -> retrieve -> ground -> verify ->
act) plus a small summarize helper into one DecodeResult. Every stage is
individually try/excepted: a failure in any single stage degrades that part
of the result to an empty/safe value rather than raising, so `run_decode`
always returns a schema-valid (if partial) DecodeResult.

Signature is frozen per CLAUDE.md: run_decode(text, jurisdiction) -> DecodeResult
"""

from __future__ import annotations

import logging
import uuid

from app.pipeline import act as act_stage
from app.pipeline import classify as classify_stage
from app.pipeline import extract as extract_stage
from app.pipeline import ground as ground_stage
from app.pipeline import retrieve as retrieve_stage
from app.pipeline import summarize as summarize_stage
from app.pipeline import verify as verify_stage
from app.schemas import (
    Action,
    Claim,
    DecodeResult,
    ExtractedFact,
    Verification,
)

logger = logging.getLogger(__name__)

DISCLAIMER = "Information, not legal advice."


def run_decode(text: str, jurisdiction: str = "IE") -> DecodeResult:
    """Run the full six-stage decode pipeline.

    Resilient by design: each stage is isolated in its own try/except so a
    failure anywhere (bad model output, network error, empty search results)
    degrades that piece of the result to empty/safe defaults instead of
    aborting the whole request. The endpoint always gets back a schema-valid
    DecodeResult.
    """
    result_id = str(uuid.uuid4())
    juris = (jurisdiction or "IE").strip() or "IE"

    doc_type = "other"
    try:
        doc_type, juris = classify_stage.classify(text, default_jurisdiction=juris)
    except Exception:
        logger.exception("classify stage failed; defaulting doc_type=other")

    facts: list[ExtractedFact] = []
    try:
        facts = extract_stage.extract(text, doc_type)
    except Exception:
        logger.exception("extract stage failed; continuing with no facts")

    urls: list[dict[str, str]] = []
    try:
        urls = retrieve_stage.retrieve(doc_type, facts, juris)
    except Exception:
        logger.exception("retrieve stage failed; continuing with no candidate URLs")

    passages: list[dict[str, str]] = []
    try:
        passages = ground_stage.ground(urls)
    except Exception:
        logger.exception("ground stage failed; continuing with no grounded passages")

    claims: list[Claim] = []
    verifications: list[Verification] = []
    try:
        claims, verifications = verify_stage.verify(doc_type, facts, passages)
    except Exception:
        logger.exception("verify stage failed; continuing with no claims/verifications")

    actions: list[Action] = []
    try:
        actions = act_stage.act(doc_type, facts, verifications, juris)
    except Exception:
        logger.exception("act stage failed; continuing with no actions")

    plain_summary = ""
    try:
        plain_summary = summarize_stage.summarize(text, doc_type, facts)
    except Exception:
        logger.exception("summarize helper failed; using generic summary")
        plain_summary = "We could not automatically generate a plain-language summary for this document."

    return DecodeResult(
        id=result_id,
        doc_type=doc_type,
        jurisdiction=juris,
        plain_summary=plain_summary,
        extracted_facts=facts,
        claims=claims,
        verification=verifications,
        actions=actions,
        disclaimer=DISCLAIMER,
    )
