"""Jurisdiction helpers — institutions are scoped by place."""

JURISDICTION_LABELS: dict[str, str] = {
    "IE": "Ireland",
    "GB": "United Kingdom",
    "UK": "United Kingdom",
    "US": "United States",
    "EU": "European Union",
}


def normalize_jurisdiction(jurisdiction: str) -> str:
    code = (jurisdiction or "IE").strip().upper()
    if code == "UK":
        return "GB"
    return code or "IE"


def jurisdiction_label(jurisdiction: str) -> str:
    code = normalize_jurisdiction(jurisdiction)
    return JURISDICTION_LABELS.get(code, code)


def body_slug(body_id: str) -> str:
    """Strip jurisdiction prefix if present: IE:rtb -> rtb."""
    if ":" in body_id:
        return body_id.split(":", 1)[1]
    return body_id


def compose_institution_id(slug: str, jurisdiction: str) -> str:
    """Unique institution key scoped to place: IE:rtb, GB:hmrc."""
    code = normalize_jurisdiction(jurisdiction)
    return f"{code}:{body_slug(slug)}"


def parse_institution_id(institution_id: str) -> tuple[str, str]:
    """Split IE:rtb -> (IE, rtb). Bare slugs default to IE for backwards compat."""
    if ":" in institution_id:
        jurisdiction, slug = institution_id.split(":", 1)
        return normalize_jurisdiction(jurisdiction), slug
    return "IE", institution_id
