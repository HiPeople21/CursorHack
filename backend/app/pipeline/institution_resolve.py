"""User prompts and resolution when government institutions are unknown."""

import re

from app.pipeline.body_registry import (
    get_body,
    get_bodies_for_doc_type,
    get_bodies_for_jurisdiction,
)
from app.pipeline.jurisdiction import body_slug, normalize_jurisdiction
from app.pipeline.types import IdentifiedBody
from app.schemas import InstitutionPrompt, InstitutionSuggestion, UserProvidedInstitution


def build_institution_prompt(doc_type: str, jurisdiction: str) -> InstitutionPrompt:
    """Build the message and registry suggestions shown when identification fails."""
    place = normalize_jurisdiction(jurisdiction)
    suggestions = _suggestions_for_doc_type(doc_type, place)
    if not suggestions:
        suggestions = _suggestions_for_jurisdiction(place)

    return InstitutionPrompt(
        message=(
            "We could not identify which government body sent or governs this document. "
            "Please tell us which institution it is so we can look up the correct rules."
        ),
        field="institution",
        suggestions=suggestions,
    )


def institution_from_user_input(
    institution: UserProvidedInstitution,
    jurisdiction: str,
) -> IdentifiedBody:
    """Turn a user-supplied institution into an IdentifiedBody for the pipeline."""
    place = normalize_jurisdiction(jurisdiction)

    if institution.body_id:
        slug = body_slug(institution.body_id)
        entry = get_body(slug)
        display_name = institution.display_name or (
            entry.display_name if entry else _title_from_slug(slug)
        )
        return IdentifiedBody(
            body_id=slug,
            display_name=display_name,
            confidence=1.0,
            jurisdiction=place,
            source_span=None,
            match_kind="user_provided",
        )

    if institution.display_name:
        return IdentifiedBody(
            body_id=_slugify(institution.display_name),
            display_name=institution.display_name.strip(),
            confidence=1.0,
            jurisdiction=place,
            source_span=None,
            match_kind="user_provided",
        )

    raise ValueError("institution requires body_id or display_name")


def _suggestions_for_doc_type(doc_type: str, jurisdiction: str) -> list[InstitutionSuggestion]:
    return [
        InstitutionSuggestion(body_id=body_id, display_name=entry.display_name)
        for body_id, entry in get_bodies_for_doc_type(doc_type, jurisdiction)
    ]


def _suggestions_for_jurisdiction(jurisdiction: str) -> list[InstitutionSuggestion]:
    return [
        InstitutionSuggestion(body_id=body_id, display_name=entry.display_name)
        for body_id, entry in get_bodies_for_jurisdiction(jurisdiction)
    ]


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug[:64] or "unknown_body"


def _title_from_slug(slug: str) -> str:
    return slug.replace("_", " ").title()
