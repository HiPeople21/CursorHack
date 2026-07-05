"""End-to-end smoke test for the money demo.

Boots the real FastAPI app (in-process, via TestClient), forces DEMO_MODE=1
(so every external client — Qwen/Exa/Firecrawl — serves canned fixtures with
no network access), POSTs the defective RTB termination notice fixture to
/api/decode, and asserts the response actually contains a Verification with
verdict == "mismatch" backed by a real, non-null Source with a verbatim quote.

This is the test that guarantees the demo is safe: if this fails, the
verification panel will not fire live on stage.

Run with:
    cd backend && DEMO_MODE=1 ../backend/.venv/bin/python -m pytest tests/test_smoke.py -v
"""

from __future__ import annotations

import os
from pathlib import Path

# DEMO_MODE must be set before the app (and its clients) import os.getenv at
# call time; our clients read os.getenv() lazily on every call, but we still
# pin it here explicitly so this test is never accidentally run against live
# APIs.
os.environ["DEMO_MODE"] = "1"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
DEFECTIVE_NOTICE_PATH = FIXTURES_DIR / "sample_docs" / "defective_rtb_notice.txt"

client = TestClient(app)


def test_health_reports_demo_mode() -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["demo_mode"] is True


def test_defective_notice_surfaces_mismatch_with_real_source() -> None:
    text = DEFECTIVE_NOTICE_PATH.read_text(encoding="utf-8")

    # The pipeline now requires the governing institution before it produces a
    # result; supply the RTB (as a user would from the needs_institution prompt)
    # so the decode runs to completion.
    resp = client.post(
        "/api/decode",
        json={
            "text": text,
            "jurisdiction": "IE",
            "institution": {"body_id": "rtb"},
        },
    )
    assert resp.status_code == 200, resp.text

    response = resp.json()
    assert response["status"] == "complete", response
    result = response["result"]
    assert result is not None, "expected a DecodeResult on a complete response"

    verifications = result["verification"]
    assert isinstance(verifications, list) and verifications, (
        "expected at least one Verification in the response"
    )

    mismatches = [v for v in verifications if v["verdict"] == "mismatch"]
    assert mismatches, f"expected a 'mismatch' verdict, got verdicts: "\
        f"{[v['verdict'] for v in verifications]}"

    mismatch = mismatches[0]

    # Never invent a citation: a mismatch verdict must carry a real Source
    # with a non-empty verbatim quote (CLAUDE.md hard rule).
    source = mismatch["source"]
    assert source is not None, "mismatch verdict must carry a non-null source"
    assert source["quote"].strip(), "source quote must not be empty"
    assert source["url"].strip(), "source url must not be empty"
    assert source["title"].strip()
    assert source["retrieved_at"].strip()

    # Sanity-check this is *the* money-demo mismatch: 14-day notice vs the
    # 90-day statutory minimum for a 3+ year tenancy.
    assert "14" in mismatch["assertion"]
    assert "90" in mismatch["rule_value"]

    # The generated actions must include at least one drafted response
    # (letter/form/email/deadline/contact) — the "generated action" half of
    # the pitch.
    assert result["actions"], "expected at least one generated action"

    # disclaimer is always populated per CLAUDE.md hard rules.
    assert result["disclaimer"].strip()
