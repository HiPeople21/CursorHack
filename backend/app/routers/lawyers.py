"""Lawyer referral endpoints — standalone recommend + location resolution helpers."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import UserProfileRow
from app.pipeline.refer_lawyers import eligibility_reason, needs_lawyer_referral, refer_lawyers
from app.routers.profile import _row_to_profile
from app.schemas import (
    LawyerRecommendRequest,
    LawyerRecommendResponse,
    LawyerSearchLocation,
)

router = APIRouter(prefix="/api/lawyers", tags=["lawyers"])


def resolve_search_location(
    db: Session,
    *,
    location: LawyerSearchLocation | None = None,
    profile_id: str | None = None,
    fallback_jurisdiction: str = "IE",
) -> LawyerSearchLocation | None:
    """Merge explicit location with profile city/county when profile_id is set."""
    if not location and not profile_id:
        return None

    resolved = location.model_copy() if location else LawyerSearchLocation()

    if profile_id:
        row = db.get(UserProfileRow, profile_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Profile not found")
        profile = _row_to_profile(row)
        if not resolved.city and profile.city:
            resolved.city = profile.city
        if not resolved.county and profile.county:
            resolved.county = profile.county
        if not resolved.jurisdiction:
            resolved.jurisdiction = profile.jurisdiction or row.jurisdiction

    if not resolved.jurisdiction:
        resolved.jurisdiction = fallback_jurisdiction

    return resolved


@router.post("/recommend", response_model=LawyerRecommendResponse)
def recommend_lawyers(
    request: LawyerRecommendRequest,
    db: Session = Depends(get_db),
) -> LawyerRecommendResponse:
    """Recommend specialist lawyers when sources are unavailable and the query is hard."""
    location = resolve_search_location(
        db,
        location=request.location,
        profile_id=request.profile_id,
        fallback_jurisdiction=request.jurisdiction,
    )

    passages: list = []
    eligible = needs_lawyer_referral(
        passages=passages,
        claims=request.claims,
        verifications=request.verification,
        facts=request.extracted_facts,
    )
    reason = eligibility_reason(
        passages=passages,
        claims=request.claims,
        verifications=request.verification,
        facts=request.extracted_facts,
    )

    if not eligible:
        return LawyerRecommendResponse(referrals=[], eligible=False, reason=reason)

    referrals = refer_lawyers(
        request.doc_type,
        request.jurisdiction,
        location,
        request.plain_summary,
        request.extracted_facts,
        passages=passages,
        claims=request.claims,
        verifications=request.verification,
    )
    return LawyerRecommendResponse(referrals=referrals, eligible=True, reason=reason)
