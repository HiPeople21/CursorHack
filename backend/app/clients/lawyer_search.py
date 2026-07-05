"""Lawyer/solicitor search via Exa with DEMO_MODE fixtures."""

import json
import os
from typing import Any

from app.clients.config import fixtures_dir, is_demo_mode
from app.clients.exa import search as exa_search
from app.pipeline.jurisdiction import jurisdiction_label, normalize_jurisdiction
from app.schemas import LawyerReferral, LawyerSearchLocation

_FIXTURE_PATH = os.path.join(fixtures_dir(), "lawyer_search_ie.json")

PRACTICE_AREAS: dict[str, str] = {
    "tenancy": "tenancy and landlord-tenant law",
    "insurance": "insurance claims and policy disputes",
    "medical_bill": "healthcare billing and medical negligence",
    "gov_letter": "administrative and public law",
    "other": "general legal advice",
}

_JURISDICTION_FIXTURES: dict[str, str] = {
    "IE": "lawyer_search_ie.json",
}


def _use_mock() -> bool:
    return is_demo_mode() or not os.getenv("EXA_API_KEY")


def _fixture_path(jurisdiction: str) -> str:
    code = normalize_jurisdiction(jurisdiction) or "IE"
    filename = _JURISDICTION_FIXTURES.get(code, "lawyer_search_ie.json")
    return os.path.join(fixtures_dir(), filename)


def _location_display(location: LawyerSearchLocation | None, jurisdiction: str) -> str:
    parts: list[str] = []
    if location and location.city:
        parts.append(location.city.strip())
    if location and location.county and location.county.strip() not in parts:
        parts.append(location.county.strip())
    if not parts:
        label = jurisdiction_label(jurisdiction)
        return label or jurisdiction or "your area"
    label = jurisdiction_label(location.jurisdiction if location and location.jurisdiction else jurisdiction)
    if label and label not in parts[-1]:
        parts.append(label)
    return ", ".join(parts)


def _build_search_query(
    doc_type: str,
    jurisdiction: str,
    location: LawyerSearchLocation | None,
) -> str:
    practice = PRACTICE_AREAS.get(doc_type, PRACTICE_AREAS["other"])
    place = _location_display(location, jurisdiction)
    label = jurisdiction_label(jurisdiction)
    role = "solicitor" if normalize_jurisdiction(jurisdiction) == "IE" else "lawyer"
    return f"{practice} {role} {place} {label}".strip()


def _referral_from_search_result(
    item: dict[str, str],
    *,
    practice_area: str,
    location: str,
    reason: str,
) -> LawyerReferral:
    title = (item.get("title") or item.get("url") or "Legal professional").strip()
    firm = title
    name = "See listing"
    if " - " in title:
        firm, name = title.split(" - ", 1)
    elif "|" in title:
        parts = [p.strip() for p in title.split("|", 1)]
        firm, name = parts[0], parts[1] if len(parts) > 1 else "See listing"
    return LawyerReferral(
        name=name.strip() or "See listing",
        firm=firm.strip() or title,
        practice_area=practice_area,
        location=location,
        url=item.get("url") or None,
        phone=None,
        reason=reason,
    )


def _load_fixture_referrals(jurisdiction: str) -> list[dict[str, Any]]:
    path = _fixture_path(jurisdiction)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("referrals", [])


def _filter_fixture_by_location(
    referrals: list[dict[str, Any]],
    location: LawyerSearchLocation | None,
) -> list[dict[str, Any]]:
    if not location or not location.city:
        return referrals
    city = location.city.strip().lower()
    matched = [
        r for r in referrals if city in (r.get("location") or "").lower()
    ]
    return matched or referrals


def search_lawyers(
    doc_type: str,
    jurisdiction: str,
    location: LawyerSearchLocation | None = None,
    *,
    reason: str,
    max_results: int = 3,
) -> list[LawyerReferral]:
    """Return specialist lawyers near the user's location for the document field."""
    practice_area = PRACTICE_AREAS.get(doc_type, PRACTICE_AREAS["other"])
    location_display = _location_display(location, jurisdiction)

    if _use_mock():
        raw = _load_fixture_referrals(jurisdiction)
        raw = _filter_fixture_by_location(raw, location)
        referrals: list[LawyerReferral] = []
        for item in raw[:max_results]:
            referrals.append(
                LawyerReferral(
                    name=item.get("name", "See listing"),
                    firm=item.get("firm", ""),
                    practice_area=item.get("practice_area", practice_area),
                    location=item.get("location", location_display),
                    url=item.get("url"),
                    phone=item.get("phone"),
                    reason=item.get("reason") or reason,
                )
            )
        return referrals

    query = _build_search_query(doc_type, jurisdiction, location)
    include_domains: list[str] | None = None
    code = normalize_jurisdiction(jurisdiction)
    if code == "IE":
        include_domains = ["lawsociety.ie", "flac.ie", "citizensinformation.ie"]

    results = exa_search(query, include_domains=include_domains, num_results=max_results)
    referrals = [
        _referral_from_search_result(
            item,
            practice_area=practice_area,
            location=location_display,
            reason=reason,
        )
        for item in results
        if item.get("url")
    ]
    return referrals[:max_results]
