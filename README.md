# Standing — Bureaucracy Decoder

Paste an official document — a tenancy termination notice, an insurance denial, a medical
bill, a government letter — and Standing extracts *your* specific facts, retrieves the
*current* governing rule for your jurisdiction, checks whether the document is even lawful,
cites every claim to a real source passage, and drafts your response. Demo jurisdiction:
Ireland (RTB, Citizens Information, gov.ie).

## Why this isn't "just ChatGPT"

A general chatbot can summarize a letter and guess whether it sounds fishy. Standing does
four things a chat window can't:

1. **Extraction** — pulls out the case-specific facts (notice period, dates, amounts) with
   the exact source span each one came from, not a generic explainer.
2. **Live grounding** — searches for and scrapes the actual current governing-rule page
   (Citizens Information / RTB / gov.ie), not the model's stale training memory.
3. **Verification** — runs entailment between what *your* document asserts and what the rule
   *actually* says, and renders a explicit verdict: `matches`, `mismatch`, or
   `cannot_determine`.
4. **Per-claim receipts** — every claim and verification is tied to a real `Source` object
   (url, title, verbatim quote, retrieved-at timestamp). If no passage can be verified to
   genuinely support a claim, the claim is marked `unverifiable`/`cannot_determine` instead —
   **no citation is ever invented.**
5. **Generated action** — an appeal letter / RTB dispute form / deadline notice that cites the
   exact rule that was verified, ready to send.

The centerpiece is the **verification panel**: "here's what they got wrong, and here's your
appeal" — not "here's what this document means."

## Stack

- Frontend: Vite + React + Tailwind
- Backend: FastAPI + SQLite (SQLAlchemy)
- External services: Qwen (LLM), Exa (search), Firecrawl (scrape) — each with a canned-fixture
  mock fallback so the whole product runs offline (see `DEMO_MODE` below).

## Setup

**Backend:**

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # DEMO_MODE=1 by default — no real API keys needed
```

**Frontend:**

```bash
cd frontend
npm install
```

## Run

From the repo root:

```bash
./dev.sh
```

This starts the FastAPI backend (`uvicorn`, reload on, using `backend/.venv` if present) and
the Vite dev server together, with `DEMO_MODE=1` by default, and prints both URLs:

```
Backend:  http://127.0.0.1:8000   (docs at /docs, health at /api/health)
Frontend: http://localhost:5173
```

Press `Ctrl-C` to stop both — `dev.sh` traps the signal and kills both processes.

The Vite dev server proxies `/api/*` to `http://localhost:8000` (see
`frontend/vite.config.ts`), and the backend's CORS middleware allows the
`http://localhost:5173` origin (see `backend/app/main.py`), so the frontend can call
relative `/api/...` paths in dev with no CORS errors either way.

To exercise the **live** path instead (real Qwen/Exa/Firecrawl calls), fill in the API keys in
`backend/.env` and run `DEMO_MODE=0 ./dev.sh`.

## `DEMO_MODE`

`DEMO_MODE=1` (the default) makes every external client (`app/clients/qwen.py`,
`app/clients/exa.py`, `app/clients/firecrawl.py`) skip the network entirely and return canned
fixtures from `backend/fixtures/` instead. This means:

- A clean checkout runs the **full six-stage pipeline** (classify → extract → retrieve →
  ground → verify → act) end-to-end with **no API keys, no network access, and no rate
  limits** — the demo can never die on a flaky scrape or an expired key.
- The results are deterministic and reproducible: the same input document always produces the
  same extracted facts, verification verdicts, and generated actions.

Set `DEMO_MODE=0` (and populate `QWEN_API_KEY` / `EXA_API_KEY` / `FIRECRAWL_API_KEY` in
`backend/.env`) to hit the real APIs instead.

## The demo script

This is the money demo: a **defective RTB termination notice** whose stated notice period is
shorter than the statutory minimum, so the verification panel fires a live **MISMATCH**.

1. Run `./dev.sh`, open `http://localhost:5173`.
2. Paste in the contents of `backend/fixtures/sample_docs/defective_rtb_notice.txt` — a notice
   dated 1 June 2026, for a tenancy that started 1 March 2021 (so it has run over 3 years),
   giving the tenant only **14 days** to vacate.
3. Click decode. The audience sees:
   - **Extracted facts**: `notice_period_days = 14`, `tenancy_start = 2021-03-01`,
     `notice_date = 2026-06-01`, `landlord_name = Kelly Properties Ltd` — each traceable to
     the exact sentence in the pasted notice.
   - **Verification panel**: a flagged **MISMATCH** —
     - assertion: *"Notice gives 14 days to vacate the property"*
     - rule value: *"90 days minimum notice for a tenancy of 3 years or more"*
     - a cited source: Citizens Information, *"Ending a tenancy"*, with the verbatim quoted
       passage *"notice period of 90 days where the tenancy has lasted 3 years or more"*.
   - **Generated action**: a drafted appeal letter to the landlord citing the exact 90-day
     rule and asserting the notice is invalid, plus an RTB-contact action.
4. The punchline: this isn't a vibe — every number on screen is either lifted verbatim from
   the pasted document or from a quoted, timestamped source passage. Nothing is invented.

### Verifying this offline, headlessly (no browser)

```bash
cd backend
DEMO_MODE=1 .venv/bin/python -m pytest tests/test_smoke.py -v
```

This posts the same defective-notice fixture straight to `/api/decode` and asserts the
response contains a `verification` item with `verdict == "mismatch"` backed by a real,
non-null `source` — the automated proof that the money demo is safe to run live.

## Repo layout

See `CLAUDE.md` for the full contract (frozen response schema, pipeline stage signatures,
external client mock-fallback rules). Key paths:

- `backend/app/schemas.py` / `frontend/src/types.ts` — the frozen response contract (kept in
  lockstep).
- `backend/app/pipeline/` — the six-stage pipeline (`classify`, `extract`, `retrieve`,
  `ground`, `verify`, `act`) plus `run.py`, which chains them and degrades gracefully if any
  single stage fails.
- `backend/app/clients/` — Qwen/Exa/Firecrawl clients, each with a `DEMO_MODE` fixture
  fallback.
- `backend/fixtures/` — canned demo documents and their Qwen/Exa/Firecrawl responses,
  including the defective RTB notice fixture used above.
- `backend/tests/test_smoke.py` — the end-to-end smoke test described above.
- `dev.sh` — boots both dev servers together.

## Disclaimer

Standing always populates a `disclaimer` field: *"Information, not legal advice."* It asserts
rights by quoting the source it retrieved, not in its own voice.
