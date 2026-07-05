"""POST /api/decode and the history GET endpoints."""

import asyncio
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.jobs import Job, get_job, start_job
from app.models import Document, SourceRow
from app.persistence import persist_result
from app.pipeline.run import run_decode
from app.schemas import (
    Action,
    Claim,
    DecodeRequest,
    DecodeResponse,
    DecodeResult,
    ExtractedFact,
    Source,
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
