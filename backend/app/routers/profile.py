"""Profile CRUD — stores user PII encrypted at rest for future document autofill."""

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.crypto import ProfileDecryptionError, decrypt_payload, encrypt_payload
from app.db import get_db
from app.models import UserProfileRow, _now_iso
from app.schemas import UserProfile, UserProfileCreate, UserProfileUpdate

router = APIRouter(prefix="/api/profile", tags=["profile"])

_PROFILE_PAYLOAD_KEYS = (
    "full_name",
    "email",
    "phone",
    "address_line1",
    "address_line2",
    "city",
    "county",
    "eircode",
    "date_of_birth",
    "pps_number",
    "extra",
)


def _payload_from_create(data: UserProfileCreate) -> dict[str, Any]:
    return {
        "full_name": data.full_name,
        "email": data.email,
        "phone": data.phone,
        "address_line1": data.address_line1,
        "address_line2": data.address_line2,
        "city": data.city,
        "county": data.county,
        "eircode": data.eircode,
        "date_of_birth": data.date_of_birth,
        "pps_number": data.pps_number,
        "extra": data.extra,
    }


def _payload_from_update(existing: dict[str, Any], data: UserProfileUpdate) -> dict[str, Any]:
    merged = dict(existing)
    for field in _PROFILE_PAYLOAD_KEYS:
        value = getattr(data, field)
        if value is not None:
            merged[field] = value
    return merged


def _row_to_profile(row: UserProfileRow) -> UserProfile:
    try:
        payload = decrypt_payload(row.encrypted_payload)
    except ProfileDecryptionError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    extra = payload.get("extra") or {}
    if isinstance(extra, str):
        extra = json.loads(extra)

    return UserProfile(
        id=row.id,
        full_name=payload.get("full_name", ""),
        email=payload.get("email"),
        phone=payload.get("phone"),
        address_line1=payload.get("address_line1", ""),
        address_line2=payload.get("address_line2"),
        city=payload.get("city", ""),
        county=payload.get("county", ""),
        eircode=payload.get("eircode"),
        date_of_birth=payload.get("date_of_birth"),
        pps_number=payload.get("pps_number"),
        jurisdiction=row.jurisdiction,
        extra=extra,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.post("", response_model=UserProfile, status_code=201)
def create_profile(
    body: UserProfileCreate,
    db: Session = Depends(get_db),
) -> UserProfile:
    """Create a profile. The client should persist the returned id (e.g. localStorage)."""
    payload = _payload_from_create(body)
    row = UserProfileRow(
        jurisdiction=body.jurisdiction,
        encrypted_payload=encrypt_payload(payload),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_profile(row)


@router.get("/{profile_id}", response_model=UserProfile)
def get_profile(profile_id: str, db: Session = Depends(get_db)) -> UserProfile:
    row = db.get(UserProfileRow, profile_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return _row_to_profile(row)


@router.put("/{profile_id}", response_model=UserProfile)
def update_profile(
    profile_id: str,
    body: UserProfileUpdate,
    db: Session = Depends(get_db),
) -> UserProfile:
    row = db.get(UserProfileRow, profile_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    try:
        existing = decrypt_payload(row.encrypted_payload)
    except ProfileDecryptionError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    payload = _payload_from_update(existing, body)
    row.jurisdiction = body.jurisdiction if body.jurisdiction is not None else row.jurisdiction
    row.encrypted_payload = encrypt_payload(payload)
    row.updated_at = _now_iso()
    db.commit()
    db.refresh(row)
    return _row_to_profile(row)


@router.delete("/{profile_id}", status_code=204)
def delete_profile(profile_id: str, db: Session = Depends(get_db)) -> None:
    row = db.get(UserProfileRow, profile_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    db.delete(row)
    db.commit()
