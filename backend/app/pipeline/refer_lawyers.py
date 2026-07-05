"""Lawyer referral stage — when verification cannot ground an answer."""

from app.clients.lawyer_search import PRACTICE_AREAS, search_lawyers
from app.pipeline.jurisdiction import jurisdiction_label
from app.pipeline.types import Passage
from app.schemas import Claim, ExtractedFact, LawyerReferral, LawyerSearchLocation, Verification


def has_usable_sources(
    passages: list[Passage],
    claims: list[Claim],
    verifications: list[Verification],
) -> bool:
    """True when at least one claim or verification is backed by a grounded source."""
    if any(c.source for c in claims):
        return True
    if any(v.source for v in verifications):
        return True
    if passages and not claims and not verifications:
        return False
    return False


def query_is_difficult(
    claims: list[Claim],
    verifications: list[Verification],
    facts: list[ExtractedFact],
) -> bool:
    """Heuristic: the document question is too hard to answer without a specialist."""
    if not verifications:
        return len(facts) >= 2 or len(claims) > 0

    cannot_determine = sum(1 for v in verifications if v.verdict == "cannot_determine")
    if cannot_determine / len(verifications) >= 0.5:
        return True

    if claims:
        unverifiable = sum(1 for c in claims if c.status == "unverifiable")
        if unverifiable / len(claims) >= 0.75:
            return True

    return len(facts) >= 5


def needs_lawyer_referral(
    passages: list[Passage],
    claims: list[Claim],
    verifications: list[Verification],
    facts: list[ExtractedFact],
) -> bool:
    """Recommend lawyers only when we lack sources and the query is sufficiently hard."""
    if has_usable_sources(passages, claims, verifications):
        return False
    return query_is_difficult(claims, verifications, facts)


def eligibility_reason(
    passages: list[Passage],
    claims: list[Claim],
    verifications: list[Verification],
    facts: list[ExtractedFact],
) -> str:
    if has_usable_sources(passages, claims, verifications):
        return "Governing sources were found — automated verification is possible."
    if not query_is_difficult(claims, verifications, facts):
        return "The query does not appear complex enough to require specialist referral."
    return "No governing sources available and the document raises questions we cannot verify."


def refer_lawyers(
    doc_type: str,
    jurisdiction: str,
    location: LawyerSearchLocation | None,
    plain_summary: str,
    facts: list[ExtractedFact],
    *,
    passages: list[Passage],
    claims: list[Claim],
    verifications: list[Verification],
) -> list[LawyerReferral]:
    """Search for field-specialist lawyers when referral criteria are met."""
    if not needs_lawyer_referral(passages, claims, verifications, facts):
        return []

    practice = PRACTICE_AREAS.get(doc_type, PRACTICE_AREAS["other"])
    place = jurisdiction_label(jurisdiction) or jurisdiction or "your jurisdiction"
    summary_hint = plain_summary[:120].rstrip()
    if summary_hint and not summary_hint.endswith("."):
        summary_hint += "…"

    reason = (
        f"We could not retrieve governing rules to verify this document. "
        f"A {practice} specialist in {place} can advise on your specific situation."
    )
    if summary_hint:
        reason = f"{reason} Document summary: {summary_hint}"

    return search_lawyers(
        doc_type,
        jurisdiction,
        location,
        reason=reason,
    )
