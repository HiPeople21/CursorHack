"""Pipeline entry point — chains classify → identify → extract → retrieve → ground → verify → act → refer.

``run_decode_stream`` is the source of truth: a generator that yields a progress
event after each stage so the frontend can show what the AI is doing, then a
terminal event carrying the full ``DecodeResponse``. ``run_decode`` simply drains
that generator and returns the final response, so the two can never drift apart.
"""

import logging
import uuid
from collections.abc import Iterator
from typing import Any

from app.pipeline.act import act
from app.pipeline.classify import classify
from app.pipeline.extract import extract
from app.pipeline.ground import ground
from app.pipeline.identify import identify_bodies
from app.pipeline.institution_resolve import (
    build_institution_prompt,
    institution_from_user_input,
)
from app.pipeline.jurisdiction import infer_jurisdiction_from_text
from app.pipeline.refer_lawyers import eligibility_reason, needs_lawyer_referral
from app.pipeline.retrieve import retrieve
from app.pipeline.verify import verify
from app.schemas import DecodeResponse, DecodeResult, UserProvidedInstitution

logger = logging.getLogger(__name__)

DISCLAIMER = "Information, not legal advice."

_DOC_TYPE_LABEL = {
    "tenancy": "tenancy notice",
    "insurance": "insurance letter",
    "medical_bill": "medical bill",
    "gov_letter": "government letter",
    "other": "document",
}


def _running(stage: str, label: str) -> dict[str, Any]:
    return {"stage": stage, "status": "running", "label": label}


def _done(stage: str, detail: str) -> dict[str, Any]:
    return {"stage": stage, "status": "done", "detail": detail}


def run_decode_stream(
    text: str,
    jurisdiction: str | None = None,
    institution: UserProvidedInstitution | None = None,
) -> Iterator[dict[str, Any]]:
    """Run the decode pipeline, yielding a progress event per stage.

    Yields progress dicts (``stage``/``status``/``label``/``detail``) and, as the
    final item, a terminal dict with a ``response`` key holding the
    ``DecodeResponse``. Degrades gracefully per stage — partial results still
    return.
    """
    doc_type = "other"
    resolved_jurisdiction = jurisdiction or ""
    bodies = []
    facts = []
    plain_summary = "Document received for analysis."
    claims = []
    verifications = []
    actions = []

    yield _running("classify", "Reading the document and working out what it is…")
    try:
        doc_type, resolved_jurisdiction = classify(text, resolved_jurisdiction or None)
    except Exception:
        logger.exception("classify failed")
        if not resolved_jurisdiction:
            resolved_jurisdiction = infer_jurisdiction_from_text(text) or "UNK"
    yield _done(
        "classify",
        f"Looks like a {_DOC_TYPE_LABEL.get(doc_type, doc_type)} · {resolved_jurisdiction}",
    )

    yield _running("identify", "Identifying the issuing authority…")
    try:
        bodies = identify_bodies(text, doc_type, resolved_jurisdiction)
    except Exception:
        logger.exception("identify_bodies failed")

    if bodies:
        names = ", ".join(b.display_name for b in bodies)
        yield _done("identify", f"Authority: {names}")
    else:
        yield _done("identify", "No authority named in the document")

    if not bodies:
        if institution is None:
            yield {
                "stage": "needs_institution",
                "status": "done",
                "response": DecodeResponse(
                    status="needs_institution",
                    institution_prompt=build_institution_prompt(
                        doc_type, resolved_jurisdiction
                    ),
                ),
            }
            return
        try:
            bodies = [institution_from_user_input(institution, resolved_jurisdiction)]
        except ValueError:
            yield {
                "stage": "needs_institution",
                "status": "done",
                "response": DecodeResponse(
                    status="needs_institution",
                    institution_prompt=build_institution_prompt(
                        doc_type, resolved_jurisdiction
                    ),
                ),
            }
            return

    yield _running("extract", "Extracting your specific facts…")
    try:
        facts, plain_summary = extract(text, doc_type)
    except Exception:
        logger.exception("extract failed")
    yield _done("extract", f"Pulled out {len(facts)} fact(s)")

    yield _running("retrieve", "Searching for the current governing rules…")
    urls: list[str] = []
    try:
        urls = retrieve(bodies, doc_type, facts, resolved_jurisdiction)
    except Exception:
        logger.exception("retrieve failed")
    yield _done("retrieve", f"Found {len(urls)} candidate source(s)")

    yield _running("ground", "Reading the source pages…")
    passages = []
    try:
        passages = ground(urls, bodies=bodies, jurisdiction=resolved_jurisdiction)
    except Exception:
        logger.exception("ground failed")
    yield _done("ground", f"Read {len(passages)} passage(s)")

    yield _running("verify", "Checking the document against the law…")
    try:
        claims, verifications = verify(facts, passages)
    except Exception:
        logger.exception("verify failed")
    mismatches = sum(1 for v in verifications if v.verdict == "mismatch")
    if mismatches:
        yield _done(
            "verify",
            f"{len(verifications)} check(s) · {mismatches} mismatch(es) found",
        )
    else:
        yield _done("verify", f"{len(verifications)} check(s) completed")

    yield _running("act", "Drafting what you can do next…")
    try:
        actions = act(doc_type, facts, verifications)
    except Exception:
        logger.exception("act failed")
    yield _done("act", f"Prepared {len(actions)} recommended action(s)")

    yield _running("refer", "Checking whether a lawyer referral applies…")
    lawyer_referral_eligible = False
    lawyer_referral_reason = ""
    try:
        lawyer_referral_eligible = needs_lawyer_referral(
            passages=passages,
            claims=claims,
            verifications=verifications,
            facts=facts,
        )
        lawyer_referral_reason = eligibility_reason(
            passages=passages,
            claims=claims,
            verifications=verifications,
            facts=facts,
        )
    except Exception:
        logger.exception("lawyer referral eligibility check failed")
    yield _done(
        "refer",
        "A specialist referral may help"
        if lawyer_referral_eligible
        else "No lawyer referral needed",
    )

    yield {
        "stage": "complete",
        "status": "done",
        "response": DecodeResponse(
            status="complete",
            lawyer_referral_eligible=lawyer_referral_eligible,
            lawyer_referral_reason=lawyer_referral_reason,
            result=DecodeResult(
                id=str(uuid.uuid4()),
                doc_type=doc_type,
                jurisdiction=resolved_jurisdiction,
                plain_summary=plain_summary,
                extracted_facts=facts,
                claims=claims,
                verification=verifications,
                actions=actions,
                disclaimer=DISCLAIMER,
            ),
        ),
    }


def run_decode(
    text: str,
    jurisdiction: str | None = None,
    institution: UserProvidedInstitution | None = None,
) -> DecodeResponse:
    """Run the decode pipeline and return the final response (non-streaming)."""
    final: DecodeResponse | None = None
    for event in run_decode_stream(text, jurisdiction, institution):
        response = event.get("response")
        if response is not None:
            final = response
    if final is None:  # pragma: no cover — generator always yields a terminal event
        raise RuntimeError("decode pipeline produced no terminal response")
    return final
