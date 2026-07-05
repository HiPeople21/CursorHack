"""Map stored profile fields to document placeholders for future autofill."""

from app.schemas import UserProfile


def profile_placeholders(profile: UserProfile) -> dict[str, str]:
    """Return bracket-style placeholders used in generated letters and forms."""
    address_parts = [
        profile.address_line1,
        profile.address_line2 or "",
        profile.city,
        profile.county,
        profile.eircode or "",
    ]
    full_address = ", ".join(part for part in address_parts if part.strip())

    return {
        "[FULL_NAME]": profile.full_name,
        "[NAME]": profile.full_name,
        "[EMAIL]": profile.email or "",
        "[PHONE]": profile.phone or "",
        "[ADDRESS]": full_address,
        "[ADDRESS_LINE1]": profile.address_line1,
        "[ADDRESS_LINE2]": profile.address_line2 or "",
        "[CITY]": profile.city,
        "[COUNTY]": profile.county,
        "[EIRCODE]": profile.eircode or "",
        "[DATE_OF_BIRTH]": profile.date_of_birth or "",
        "[PPS_NUMBER]": profile.pps_number or "",
        **{f"[{key.upper()}]": value for key, value in profile.extra.items()},
    }


def apply_placeholders(text: str, placeholders: dict[str, str]) -> str:
    """Replace known placeholders in generated document text."""
    result = text
    for token, value in placeholders.items():
        if value:
            result = result.replace(token, value)
    return result
