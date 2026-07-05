"""POST /api/decode and the history GET endpoints."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
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
from app.pipeline.ingest import ingest_document
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


@router.post("/decode/demo", response_model=DecodeResult)
def decode_demo(db: Session = Depends(get_db)) -> DecodeResult:
    """Offline "money demo": run the whole pipeline against the canned defective
    RTB-notice fixtures — no network, no OCR binary, no request body. This is the
    former DEMO_MODE, now an explicit endpoint instead of a global env flag.

    Ingesting the fixture first gives us the exact source text the extract spans
    are quoted from, so the returned facts keep their verbatim spans.
    """
    ingested = ingest_document(b"", "", "", demo=True)
    result = run_decode(ingested.full_text_markdown, ingested.jurisdiction, demo=True)
    result.doc_type = ingested.doc_type or result.doc_type

    doc = _persist(result, ingested.full_text_markdown)
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return result


MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB
_ALLOWED_EXTS = (".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".tif", ".tiff", ".bmp")


@router.post("/decode/upload", response_model=DecodeResult)
async def decode_upload(
    file: UploadFile = File(...),
    jurisdiction: str = Form("IE"),
    db: Session = Depends(get_db),
) -> DecodeResult:
    """Upload an image or PDF of a document, ingest it to layout-preserving
    markdown, then run the pipeline. Sibling of the JSON POST /api/decode."""
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 20 MB)")

    ctype = (file.content_type or "").lower()
    fname = file.filename or ""
    allowed = (
        ctype == "application/pdf"
        or ctype.startswith("image/")
        or fname.lower().endswith(_ALLOWED_EXTS)
    )
    if not allowed:
        raise HTTPException(
            status_code=415, detail=f"Unsupported file type: {ctype or fname or 'unknown'}"
        )

    try:
        ingested = ingest_document(data, fname, ctype)
    except Exception as exc:  # noqa: BLE001 — surface a clean 422, not a 500
        raise HTTPException(status_code=422, detail=f"Could not read document: {exc}")

    result = run_decode(ingested.full_text_markdown, jurisdiction)
    # The vision ingest actually saw the document — trust its classification.
    result.doc_type = ingested.doc_type or result.doc_type

    doc = _persist(result, ingested.full_text_markdown)
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
