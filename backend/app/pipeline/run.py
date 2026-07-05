"""Pipeline entry point.

`run_decode(text, jurisdiction) -> DecodeResult` (signature frozen per CLAUDE.md).

This branch (`extraction-layer`) implements the front of the pipeline:
**classify** and **extract** run for real over the document text, so
`doc_type`, `jurisdiction`, and `extracted_facts` reflect the actual document
that was pasted or uploaded. The downstream stages (retrieve/ground/verify/act)
are not implemented yet — those belong to other branches.

On the live path they stay empty (an honest partial result); the hardcoded
"money demo" content is served ONLY by the demo path (`demo=True`, exposed via
POST /api/decode/demo), never leaking into a real decode.

Every real stage is wrapped so any failure degrades gracefully; a single flaky
call never takes the endpoint down.
"""

import uuid
from datetime import datetime, timezone

from app.pipeline.classify import classify
from app.pipeline.extract import extract_facts
from app.schemas import (
    Action,
    Claim,
    DecodeResult,
    ExtractedFact,
    Source,
    Verification,
)


DISCLAIMER = "Information, not legal advice."


def _live_result(jurisdiction: str) -> DecodeResult:
    """Base result for a real (non-demo) decode.

    classify + extract fill in ``doc_type``, ``jurisdiction`` and
    ``extracted_facts``. The downstream stages (retrieve/ground/verify/act) are
    not implemented on this branch, so their fields stay empty rather than being
    back-filled with canned money-demo content — a real decode must never claim
    to have verified a document it never looked at.
    """
    return DecodeResult(
        id=str(uuid.uuid4()),
        doc_type="other",
        jurisdiction=jurisdiction or "IE",
        plain_summary="",
        extracted_facts=[],
        claims=[],
        verification=[],
        actions=[],
        disclaimer=DISCLAIMER,
    )


def _stub_result(jurisdiction: str) -> DecodeResult:
    """The canned defective-RTB-notice result — the offline "money demo" only.

    Served by POST /api/decode/demo (``demo=True``). NOT used for the live
    POST /api/decode path, which must reflect the actual pasted/uploaded doc.
    """
    retrieved_at = datetime.now(timezone.utc).isoformat()

    rtb_source = Source(
        url="https://www.citizensinformation.ie/en/housing/renting-a-home/tenants-and-landlords/ending-a-tenancy/",
        title="Ending a tenancy - Citizens Information",
        quote="notice period of 90 days where the tenancy has lasted 3 years or more",
        retrieved_at=retrieved_at,
    )

    return DecodeResult(
        id=str(uuid.uuid4()),
        doc_type="tenancy",
        jurisdiction=jurisdiction or "IE",
        plain_summary=(
            "This is a termination notice from your landlord ending your "
            "tenancy. It states you must leave within 14 days, but the "
            "notice period it gives appears shorter than the legal minimum "
            "for a tenancy of your length."
        ),
        extracted_facts=[
            ExtractedFact(
                key="notice_period_days",
                value="14",
                span="you are required to vacate the property within 14 days",
            ),
            ExtractedFact(
                key="tenancy_start",
                value="2021-03-01",
                span="tenancy commencing 1 March 2021",
            ),
        ],
        claims=[
            Claim(
                statement="The landlord issued a termination notice giving 14 days to vacate.",
                status="supported",
                source=None,
            ),
            Claim(
                statement="Tenancies of 3+ years require 90 days' notice in Ireland.",
                status="contradicted",
                source=rtb_source,
            ),
        ],
        verification=[
            Verification(
                assertion="14 days to vacate",
                rule_value="90 days minimum (tenancy of 3+ years)",
                verdict="mismatch",
                explanation=(
                    "For a tenancy that has lasted 3 years or more, Irish "
                    "law (RTB) requires a minimum notice period of 90 days. "
                    "This notice gives only 14, well short of the statutory "
                    "minimum."
                ),
                source=rtb_source,
            )
        ],
        actions=[
            Action(
                title="Appeal letter to landlord",
                kind="letter",
                body=(
                    "I am writing regarding the Notice of Termination dated "
                    "[DATE]. Under the Residential Tenancies Act, a tenancy "
                    "of my duration requires a minimum notice period of 90 "
                    "days, not the 14 days stated. As such, this notice is "
                    "invalid and I am not required to vacate on the date "
                    "given. I reserve my right to remain in the property "
                    "and to refer this matter to the RTB if necessary."
                ),
                deadline=None,
            ),
            Action(
                title="Respond before purported vacate date",
                kind="deadline",
                body="Notice states you must leave within 14 days of receipt.",
                deadline=None,
            ),
        ],
        disclaimer=DISCLAIMER,
    )


def run_decode(text: str, jurisdiction: str = "IE", demo: bool = False) -> DecodeResult:
    """Chain the pipeline. classify + extract are real; the rest is still stubbed.

    When ``demo`` is set the whole pipeline serves the canned "money demo"
    fixtures (POST /api/decode/demo). Otherwise this is a live decode of the
    actual document: classify + extract run for real and the unimplemented
    downstream stages stay empty — we never back-fill with the canned RTB
    content, so the result always reflects the document that was submitted.

    Resilient: each real stage degrades gracefully on any error so a partial
    result is always returned.
    """
    result = _stub_result(jurisdiction) if demo else _live_result(jurisdiction)

    try:
        doc_type, detected_jur = classify(text, demo=demo)
        result.doc_type = doc_type
        result.jurisdiction = jurisdiction or detected_jur or "IE"
    except Exception:
        pass  # keep the base doc_type/jurisdiction

    try:
        facts = extract_facts(text, result.doc_type, demo=demo)
        if demo:
            if facts:
                result.extracted_facts = facts  # keep canned facts if fixture empty
        else:
            result.extracted_facts = facts
    except Exception:
        pass  # keep whatever the base provided

    return result
