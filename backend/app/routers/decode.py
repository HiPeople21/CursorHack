"""POST /api/decode and the history GET endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    ActionRow,
    ClaimRow,
    Document,
    ExtractedFactRow,
    SourceRow,
    VerificationRow,
)
from app.pipeline.run import run_decode
from app.schemas import (
    Action,
    Claim,
    DecodeRequest,
    DecodeResult,
    ExtractedFact,
    Source,
    Verification,
)

router = APIRouter(prefix="/api", tags=["decode"])


def _persist(result: DecodeResult, raw_text: str) -> Document:
    """Write a DecodeResult (and its nested children) to SQLite.

    Uses the DecodeResult's own id as the documents.id primary key so the
    stored row and the returned payload agree.
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


def _source_to_schema(row: SourceRow | None) -> Source | None:
    if row is None:
        return None
    return Source(url=row.url, title=row.title, quote=row.quote, retrieved_at=row.retrieved_at)


def _document_to_result(doc: Document) -> DecodeResult:
    return DecodeResult(
        id=doc.id,
        doc_type=doc.doc_type,
        jurisdiction=doc.jurisdiction,
        plain_summary=doc.plain_summary,
        extracted_facts=[
            ExtractedFact(key=f.key, value=f.value, span=f.span) for f in doc.extracted_facts
        ],
        claims=[
            Claim(statement=c.statement, status=c.status, source=_source_to_schema(c.source))
            for c in doc.claims
        ],
        verification=[
            Verification(
                assertion=v.assertion,
                rule_value=v.rule_value,
                verdict=v.verdict,
                explanation=v.explanation,
                source=_source_to_schema(v.source),
            )
            for v in doc.verifications
        ],
        actions=[
            Action(title=a.title, kind=a.kind, body=a.body, deadline=a.deadline)
            for a in doc.actions
        ],
        disclaimer=doc.disclaimer,
    )


@router.post("/decode", response_model=DecodeResult)
def decode(request: DecodeRequest, db: Session = Depends(get_db)) -> DecodeResult:
    result = run_decode(request.text, request.jurisdiction)

    doc = _persist(result, request.text)
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return result


@router.get("/documents", response_model=list[DecodeResult])
def list_documents(db: Session = Depends(get_db)) -> list[DecodeResult]:
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    return [_document_to_result(doc) for doc in docs]


@router.get("/documents/{document_id}", response_model=DecodeResult)
def get_document(document_id: str, db: Session = Depends(get_db)) -> DecodeResult:
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return _document_to_result(doc)
