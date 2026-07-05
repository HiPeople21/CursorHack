"""Pydantic request/response models — THE CONTRACT.

Mirrors CLAUDE.md exactly. Do not add or remove fields here without
updating CLAUDE.md and frontend/src/types.ts in lockstep.
"""

from typing import Literal, Optional

from pydantic import BaseModel


class Source(BaseModel):
    url: str
    title: str
    quote: str  # <15 words, verbatim from the page — this is the "receipt"
    retrieved_at: str  # ISO timestamp


class ExtractedFact(BaseModel):
    key: str  # e.g. "notice_period_days", "amount_due", "tenancy_start"
    value: str
    span: Optional[str] = None  # the exact text in the source doc it came from


class Claim(BaseModel):
    statement: str
    status: Literal["supported", "contradicted", "unverifiable"]
    source: Optional[Source] = None


class Verification(BaseModel):
    assertion: str  # what the LETTER claims ("14 days to respond")
    rule_value: str  # what the STATUTE says ("28 days minimum")
    verdict: Literal["matches", "mismatch", "cannot_determine"]
    explanation: str
    source: Optional[Source] = None


class Action(BaseModel):
    title: str
    kind: Literal["letter", "form", "email", "deadline", "contact"]
    body: str  # drafted text, or contact/deadline detail
    deadline: Optional[str] = None


class DecodeResult(BaseModel):
    id: str
    doc_type: Literal["tenancy", "insurance", "medical_bill", "gov_letter", "other"]
    jurisdiction: str
    plain_summary: str
    extracted_facts: list[ExtractedFact]
    claims: list[Claim]
    verification: list[Verification]  # the centerpiece — document vs rule
    actions: list[Action]
    disclaimer: str


class DecodeRequest(BaseModel):
    text: str
    jurisdiction: str = "IE"
    institution: Optional["UserProvidedInstitution"] = None


class UserProvidedInstitution(BaseModel):
    """Supplied by the user when automatic institution identification fails."""

    body_id: Optional[str] = None  # registry slug, e.g. rtb or IE:rtb
    display_name: Optional[str] = None  # free text when slug is unknown


class InstitutionSuggestion(BaseModel):
    body_id: str
    display_name: str


class InstitutionPrompt(BaseModel):
    message: str
    field: str = "institution"
    suggestions: list[InstitutionSuggestion] = []


class DecodeResponse(BaseModel):
    status: Literal["complete", "needs_institution"]
    institution_prompt: Optional[InstitutionPrompt] = None
    result: Optional[DecodeResult] = None


# --- Profile (autofill) — not part of the frozen DecodeResult contract ---


class UserProfile(BaseModel):
    id: str
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address_line1: str = ""
    address_line2: Optional[str] = None
    city: str = ""
    county: str = ""
    eircode: Optional[str] = None
    date_of_birth: Optional[str] = None  # ISO date YYYY-MM-DD
    pps_number: Optional[str] = None
    jurisdiction: str = "IE"
    extra: dict[str, str] = {}
    created_at: str
    updated_at: str


class UserProfileCreate(BaseModel):
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address_line1: str = ""
    address_line2: Optional[str] = None
    city: str = ""
    county: str = ""
    eircode: Optional[str] = None
    date_of_birth: Optional[str] = None
    pps_number: Optional[str] = None
    jurisdiction: str = "IE"
    extra: dict[str, str] = {}


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    county: Optional[str] = None
    eircode: Optional[str] = None
    date_of_birth: Optional[str] = None
    pps_number: Optional[str] = None
    jurisdiction: Optional[str] = None
    extra: Optional[dict[str, str]] = None
