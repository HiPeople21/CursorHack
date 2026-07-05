"""Shared persistence: write a DecodeResult (and children) to SQLite.

Extracted from routers/decode.py so both the request handlers and the
background job runner (app/jobs.py) can persist without a circular import.
"""

from app.models import (
    ActionRow,
    ClaimRow,
    Document,
    ExtractedFactRow,
    SourceRow,
    VerificationRow,
)
from app.schemas import Source


def persist_result(result, raw_text: str) -> Document:
    """Build a Document ORM tree from a DecodeResult.

    Uses the DecodeResult's own id as the documents.id primary key so the
    stored row and the returned payload agree. The caller is responsible for
    adding the returned Document to a session and committing.
    """
    doc = Document(
        id=result.id,
        raw_text=raw_text,
        doc_type=result.doc_type,
        jurisdiction=result.jurisdiction,
        plain_summary=result.plain_summary,
        disclaimer=result.disclaimer,
    )

    def _make_source_row(source: Source | None) -> SourceRow | None:
        if source is None:
            return None
        row = SourceRow(
            document_id=doc.id,
            url=source.url,
            title=source.title,
            quote=source.quote,
            retrieved_at=source.retrieved_at,
        )
        doc.sources.append(row)
        return row

    for fact in result.extracted_facts:
        doc.extracted_facts.append(
            ExtractedFactRow(document_id=doc.id, key=fact.key, value=fact.value, span=fact.span)
        )

    for claim in result.claims:
        source_row = _make_source_row(claim.source)
        doc.claims.append(
            ClaimRow(
                document_id=doc.id,
                statement=claim.statement,
                status=claim.status,
                source=source_row,
            )
        )

    for verification in result.verification:
        source_row = _make_source_row(verification.source)
        doc.verifications.append(
            VerificationRow(
                document_id=doc.id,
                assertion=verification.assertion,
                rule_value=verification.rule_value,
                verdict=verification.verdict,
                explanation=verification.explanation,
                source=source_row,
            )
        )

    for action in result.actions:
        doc.actions.append(
            ActionRow(
                document_id=doc.id,
                title=action.title,
                kind=action.kind,
                body=action.body,
                deadline=action.deadline,
            )
        )

    return doc
