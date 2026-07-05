"""Stage 4: retrieve candidate governing-rule URLs from the institution corpus."""

from app.pipeline.institution_store import get_links_for_institutions
from app.pipeline.types import IdentifiedBody
from app.schemas import ExtractedFact


def retrieve(
    bodies: list[IdentifiedBody],
    doc_type: str,
    facts: list[ExtractedFact],
    jurisdiction: str,
) -> list[str]:
    """Return working legal-document URLs from the persistent institution database.

  For unknown institutions, discovers links via search and persists them.
  For broken links, re-searches and stores replacements.
    """
    return get_links_for_institutions(bodies, doc_type, facts, jurisdiction)
