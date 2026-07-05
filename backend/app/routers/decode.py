"""POST /api/decode and the history GET endpoints."""

import asyncio
import json
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.clients.config import is_demo_mode
from app.db import get_db
from app.jobs import Job, get_job, start_job
from app.models import Document, SourceRow
from app.persistence import persist_result
from app.pipeline.ingest import ingest_document
from app.pipeline.run import run_decode
from app.schemas import (
    Action,
    Claim,
    DecodeRequest,
    DecodeResponse,
    DecodeResult,
    ExtractedFact,
    Source,
    UserProvidedInstitution,
    Verification,
)

router = APIRouter(prefix="/api", tags=["decode"])


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


@router.post("/decode", response_model=DecodeResponse)
def decode(request: DecodeRequest, db: Session = Depends(get_db)) -> DecodeResponse:
    outcome = run_decode(request.text, request.jurisdiction, request.institution)

    if outcome.status != "complete" or outcome.result is None:
        return outcome

    doc = persist_result(outcome.result, request.text)
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return outcome


@router.post("/decode/demo", response_model=DecodeResult)
def decode_demo(db: Session = Depends(get_db)) -> DecodeResult:
    """Offline "money demo": run the whole pipeline against the canned defective
    RTB-notice fixtures — no network, no OCR binary, no request body. This is the
    former DEMO_MODE, now an explicit endpoint instead of a global env flag.

    Ingesting the fixture first gives us the exact source text the extract spans
    are quoted from, so the returned facts keep their verbatim spans.
    """
    ingested = ingest_document(b"", "", "", demo=True)
    outcome = run_decode(ingested.full_text_markdown, ingested.jurisdiction)
    if outcome.result is None:
        raise HTTPException(status_code=502, detail="Demo pipeline did not complete")
    result = outcome.result
    result.doc_type = ingested.doc_type or result.doc_type

    doc = persist_result(result, ingested.full_text_markdown)
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return result


MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB
_ALLOWED_EXTS = (".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".tif", ".tiff", ".bmp")


@router.post("/decode/upload", response_model=DecodeResponse)
async def decode_upload(
    file: UploadFile = File(...),
    jurisdiction: str = Form("IE"),
    institution_body_id: str | None = Form(None),
    institution_name: str | None = Form(None),
    db: Session = Depends(get_db),
) -> DecodeResponse:
    """Upload an image or PDF of a document, ingest it to layout-preserving
    markdown, then run the pipeline. Sibling of the JSON POST /api/decode.

    Returns a DecodeResponse so the upload flow mirrors the paste flow: when no
    governing body can be identified the response is ``needs_institution`` with a
    prompt, and the client can re-upload with ``institution_body_id`` /
    ``institution_name`` set to complete the decode.
    """
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
        # In DEMO_MODE, use the canned ingest fixture so the drop-in flow works
        # offline without a Tesseract binary. Live mode does real OCR/vision.
        ingested = ingest_document(data, fname, ctype, demo=is_demo_mode())
    except Exception as exc:  # noqa: BLE001 — surface a clean 422, not a 500
        raise HTTPException(status_code=422, detail=f"Could not read document: {exc}")

    institution: UserProvidedInstitution | None = None
    if institution_body_id or institution_name:
        institution = UserProvidedInstitution(
            body_id=institution_body_id or None,
            display_name=institution_name or None,
        )

    outcome = run_decode(ingested.full_text_markdown, jurisdiction, institution)

    if outcome.status != "complete" or outcome.result is None:
        return outcome

    # The vision ingest actually saw the document — trust its classification.
    outcome.result.doc_type = ingested.doc_type or outcome.result.doc_type

    doc = persist_result(outcome.result, ingested.full_text_markdown)
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return outcome


_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


async def _tail_job(job: Job):
    """Yield SSE frames for a job: replay buffered events, then stream live ones.

    Because the job runs in its own thread, a disconnecting client (browser
    refresh) does not stop the work — a later reconnect replays from index 0 and
    continues until the terminal frame.
    """
    index = 0
    while True:
        new_events, done = job.snapshot(index)
        for frame in new_events:
            yield f"data: {json.dumps(frame)}\n\n"
        index += len(new_events)
        if done and not new_events:
            break
        await asyncio.sleep(0.15)


@router.post("/decode/stream")
def decode_stream(
    request: DecodeRequest, job_id: str | None = None
) -> StreamingResponse:
    """Start a decode job and stream its progress as Server-Sent Events.

    The job runs in a background thread and persists its result independently of
    this connection, so the client can disconnect (refresh) and later reconnect
    via GET /decode/stream/{job_id}. Pass a stable job_id (the client uses its
    session id) to make reconnection possible.
    """
    resolved_id = job_id or str(uuid.uuid4())
    job = start_job(resolved_id, request.text, request.jurisdiction, request.institution)
    return StreamingResponse(
        _tail_job(job), media_type="text/event-stream", headers=_SSE_HEADERS
    )


@router.get("/decode/stream/{job_id}")
def resume_decode_stream(job_id: str) -> StreamingResponse:
    """Reconnect to an in-flight or recently finished decode job.

    Replays all buffered progress events, then streams any remaining ones. 404
    if the job is unknown (never started, or lost to a server restart / TTL).
    """
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Decode job not found")
    return StreamingResponse(
        _tail_job(job), media_type="text/event-stream", headers=_SSE_HEADERS
    )


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
