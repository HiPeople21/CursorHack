"""In-memory decode job registry with background execution.

A decode job runs in a daemon thread, decoupled from the HTTP request that
started it. Progress events are buffered on the job so that a client which
disconnects (e.g. a browser refresh) can reconnect and replay everything so
far, then continue streaming live. The FastAPI process keeps running across a
client refresh, so the work — and its buffered events — survive.

State is process-local: a server restart loses in-flight jobs (the client then
gets a 404 on reconnect and can re-run).
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from app.clients.config import is_demo_mode
from app.db import SessionLocal
from app.persistence import persist_result
from app.pipeline.ingest import ingest_document
from app.pipeline.run import run_decode_stream
from app.schemas import DecodeResponse, UserProvidedInstitution

logger = logging.getLogger(__name__)

# Keep finished jobs around long enough for a refreshed client to reconnect and
# collect the terminal frame, then let them be purged.
_JOB_TTL_SECONDS = 30 * 60


@dataclass
class Job:
    id: str
    raw_text: str
    events: list[dict[str, Any]] = field(default_factory=list)
    done: bool = False
    created_at: float = field(default_factory=time.time)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def append(self, frame: dict[str, Any]) -> None:
        with self.lock:
            self.events.append(frame)

    def snapshot(self, from_index: int) -> tuple[list[dict[str, Any]], bool]:
        """Return (events since from_index, done)."""
        with self.lock:
            return self.events[from_index:], self.done


_REGISTRY: dict[str, Job] = {}
_REGISTRY_LOCK = threading.Lock()


def _purge_expired() -> None:
    cutoff = time.time() - _JOB_TTL_SECONDS
    stale = [jid for jid, job in _REGISTRY.items() if job.done and job.created_at < cutoff]
    for jid in stale:
        _REGISTRY.pop(jid, None)


def get_job(job_id: str) -> Job | None:
    with _REGISTRY_LOCK:
        return _REGISTRY.get(job_id)


def start_job(
    job_id: str,
    text: str,
    jurisdiction: str | None,
    institution: UserProvidedInstitution | None,
) -> Job:
    """Create a fresh job for job_id (replacing any prior run) and start it."""
    job = Job(id=job_id, raw_text=text)
    with _REGISTRY_LOCK:
        _purge_expired()
        _REGISTRY[job_id] = job

    thread = threading.Thread(
        target=_run_job,
        args=(job, jurisdiction, institution),
        name=f"decode-job-{job_id}",
        daemon=True,
    )
    thread.start()
    return job


def start_upload_job(
    job_id: str,
    data: bytes,
    filename: str,
    content_type: str,
    jurisdiction: str | None,
    institution: UserProvidedInstitution | None,
) -> Job:
    """Create a fresh upload job (ingest → decode) for job_id and start it."""
    job = Job(id=job_id, raw_text="")
    with _REGISTRY_LOCK:
        _purge_expired()
        _REGISTRY[job_id] = job

    thread = threading.Thread(
        target=_run_upload_job,
        args=(job, data, filename, content_type, jurisdiction, institution),
        name=f"decode-upload-job-{job_id}",
        daemon=True,
    )
    thread.start()
    return job


def _pump_events(job: Job, events, doc_type_override: str | None = None) -> None:
    """Append pipeline events to the job, persisting the terminal result."""
    for event in events:
        response: DecodeResponse | None = event.get("response")
        if response is not None:
            if response.status == "complete" and response.result is not None:
                if doc_type_override:
                    # The vision ingest actually saw the document — trust its
                    # classification (mirrors POST /decode/upload).
                    response.result.doc_type = doc_type_override
                _persist_completed(response, job.raw_text)
            job.append(
                {
                    "stage": event["stage"],
                    "status": event["status"],
                    "response": response.model_dump(),
                }
            )
        else:
            job.append(event)


def _run_job(
    job: Job,
    jurisdiction: str | None,
    institution: UserProvidedInstitution | None,
) -> None:
    try:
        _pump_events(job, run_decode_stream(job.raw_text, jurisdiction, institution))
    except Exception:
        logger.exception("decode job %s failed", job.id)
        job.append(
            {
                "stage": "error",
                "status": "done",
                "detail": "The decode failed on the server. Please try again.",
            }
        )
    finally:
        with job.lock:
            job.done = True


def _run_upload_job(
    job: Job,
    data: bytes,
    filename: str,
    content_type: str,
    jurisdiction: str | None,
    institution: UserProvidedInstitution | None,
) -> None:
    try:
        job.append(
            {"stage": "ingest", "status": "running", "label": "Reading your file…"}
        )
        try:
            # DEMO_MODE uses the canned ingest fixture so upload works offline
            # without a Tesseract binary; live mode does real OCR/vision.
            ingested = ingest_document(
                data, filename, content_type, demo=is_demo_mode()
            )
        except Exception as exc:  # noqa: BLE001 — surface a clean error frame
            logger.exception("upload job %s ingest failed", job.id)
            job.append(
                {
                    "stage": "error",
                    "status": "done",
                    "detail": f"Could not read document: {exc}",
                }
            )
            return
        job.raw_text = ingested.full_text_markdown
        job.append(
            {"stage": "ingest", "status": "done", "detail": "Converted your file to text"}
        )
        _pump_events(
            job,
            run_decode_stream(ingested.full_text_markdown, jurisdiction, institution),
            doc_type_override=ingested.doc_type or None,
        )
    except Exception:
        logger.exception("decode upload job %s failed", job.id)
        job.append(
            {
                "stage": "error",
                "status": "done",
                "detail": "The decode failed on the server. Please try again.",
            }
        )
    finally:
        with job.lock:
            job.done = True


def _persist_completed(response: DecodeResponse, raw_text: str) -> None:
    db = SessionLocal()
    try:
        doc = persist_result(response.result, raw_text)
        db.add(doc)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("failed to persist decode result")
    finally:
        db.close()
