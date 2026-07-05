"""Pipeline entry point.

STUB — the real implementation (classify/extract/retrieve/ground/verify/act)
belongs to the pipeline-engineer. This stub returns a fully-populated,
schema-valid DecodeResult built from a hardcoded example (the "money demo":
a defective RTB termination notice) so the /api/decode endpoint is
testable end-to-end immediately.

Signature is frozen per CLAUDE.md: run_decode(text, jurisdiction) -> DecodeResult
"""

import uuid
from datetime import datetime, timezone

from app.schemas import (
    Action,
    Claim,
    DecodeResult,
    ExtractedFact,
    Source,
    Verification,
)


def run_decode(text: str, jurisdiction: str = "IE") -> DecodeResult:
    """Stub implementation — replace with the real 6-stage pipeline.

    Currently ignores `text`/`jurisdiction` content and always returns the
    canned defective-notice example so downstream (routers, frontend) can be
    built and tested against a realistic, fully-populated shape.
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
        disclaimer="Information, not legal advice.",
    )
