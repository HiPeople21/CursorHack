"""Pipeline-internal types — NOT part of the frozen DecodeResult contract."""

from typing import Literal, Optional

from pydantic import BaseModel


class IdentifiedBody(BaseModel):
    body_id: str
    display_name: str
    confidence: float
    jurisdiction: Optional[str] = None  # ISO code; defaults to pipeline jurisdiction
    source_span: Optional[str] = None
    match_kind: Literal[
        "letterhead", "signature", "reference", "explicit", "inferred", "user_provided"
    ]


class Passage(BaseModel):
    passage_id: str
    body_id: Optional[str] = None
    url: str
    title: str
    section_heading: Optional[str] = None
    text: str
    retrieved_at: str
    chunk_index: int
