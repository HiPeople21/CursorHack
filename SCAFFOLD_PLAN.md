# Scaffolding Plan — "Standing" (Bureaucracy Decoder)

A Claude Code build plan using **Sonnet as the master orchestrator** and four **project subagents** for parallel scaffolding. Stack: Vite + React + Tailwind frontend, FastAPI backend, SQLite. External services: Qwen (LLM), Exa (search), Firecrawl (scrape).

---

## 0. How the orchestration actually works

Claude Code subagents live as markdown files in `.claude/agents/`, each with its own isolated context window, tool permissions, and system prompt. Two facts drive this whole plan:

1. **Subagents cannot spawn subagents.** So the "master agent" is your *main interactive session* — start it with Sonnet (`claude --model sonnet` or `/model sonnet`). It is the only thing that delegates. The four subagents below are workers it hands scoped tasks to and gets results back from.
2. **The contract must exist before any worker runs.** Subagents each see only their own context, not each other's. If they don't build against a frozen interface, they diverge and integration fails. So **Phase 0 (master, no delegation) writes the shared contract into `CLAUDE.md` + schema files.** Everything after codes to that.

Subagents are loaded at session start — if you create the agent files by hand, restart the session (or create them via `/agents`, which takes effect immediately).

The four workers map cleanly to a 4-person team, so you can also just assign one human per subagent if you'd rather drive them manually.

```
main session (Sonnet) = MASTER ORCHESTRATOR
   │  writes CLAUDE.md + contract (Phase 0)
   ├─▶ backend-engineer     (FastAPI skeleton + SQLite models)      ─┐ parallel
   ├─▶ frontend-engineer    (Vite/React/Tailwind shell + UI)        ─┘ (Phase 1)
   ├─▶ pipeline-engineer    (the 6-stage decode pipeline + clients)    (Phase 2)
   └─▶ integration-engineer (env, fixtures, demo mode, smoke test)     (Phase 3)
```

---

## 1. Target repo layout

```
standing/
├── CLAUDE.md                     # shared contract — master writes this first
├── .claude/agents/               # the four subagents
│   ├── backend-engineer.md
│   ├── frontend-engineer.md
│   ├── pipeline-engineer.md
│   └── integration-engineer.md
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI app + CORS
│   │   ├── db.py                 # SQLite engine/session (SQLAlchemy)
│   │   ├── models.py             # ORM tables
│   │   ├── schemas.py            # pydantic request/response — THE CONTRACT
│   │   ├── routers/decode.py     # POST /api/decode, history endpoints
│   │   ├── pipeline/             # the product logic (pipeline-engineer)
│   │   │   ├── classify.py
│   │   │   ├── extract.py
│   │   │   ├── retrieve.py
│   │   │   ├── ground.py
│   │   │   ├── verify.py
│   │   │   ├── act.py
│   │   │   └── run.py            # orchestrates the six stages
│   │   └── clients/              # external APIs, each with mock fallback
│   │       ├── qwen.py
│   │       ├── exa.py
│   │       └── firecrawl.py
│   ├── fixtures/                 # canned inputs + outputs for DEMO_MODE
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/client.ts         # typed fetch, mirrors schemas.py
│   │   ├── types.ts              # TS mirror of the contract
│   │   ├── components/
│   │   │   ├── PasteBox.tsx
│   │   │   ├── ResultView.tsx
│   │   │   ├── ClaimCard.tsx     # per-claim citation rendering
│   │   │   ├── VerificationPanel.tsx  # the "they can't do that" flags
│   │   │   └── ActionCard.tsx    # generated letter/form/deadline
│   │   └── App.tsx
│   ├── index.html
│   ├── tailwind.config.js
│   └── package.json
├── dev.sh                        # one command to run both servers
└── README.md
```

---

## 2. The contract (goes into `CLAUDE.md`)

This is the single most important artifact. The master writes it verbatim before delegating anything. Every subagent reads `CLAUDE.md` automatically as project context.

### Product in one line
Paste an official document → we extract *your* specific facts, retrieve the *current* governing rule, **check whether the document is even lawful**, cite every claim to a passage, and generate the response. Not "here's what it means" — "here's what they got wrong and here's your appeal." Demo jurisdiction: Ireland (RTB, Citizens Information, gov.ie).

### Response schema — freeze this first (`backend/app/schemas.py`)

```python
# Pydantic models. The TS types in frontend/src/types.ts MUST mirror these exactly.

class Source(BaseModel):
    url: str
    title: str
    quote: str          # <15 words, verbatim from the page — this is the "receipt"
    retrieved_at: str   # ISO timestamp

class ExtractedFact(BaseModel):
    key: str            # e.g. "notice_period_days", "amount_due", "tenancy_start"
    value: str
    span: str | None    # the exact text in the source doc it came from

class Claim(BaseModel):
    statement: str
    status: Literal["supported", "contradicted", "unverifiable"]
    source: Source | None

class Verification(BaseModel):
    assertion: str      # what the LETTER claims ("14 days to respond")
    rule_value: str     # what the STATUTE says ("28 days minimum")
    verdict: Literal["matches", "mismatch", "cannot_determine"]
    explanation: str
    source: Source | None

class Action(BaseModel):
    title: str
    kind: Literal["letter", "form", "email", "deadline", "contact"]
    body: str           # drafted text, or contact/deadline detail
    deadline: str | None

class DecodeResult(BaseModel):
    id: str
    doc_type: Literal["tenancy", "insurance", "medical_bill", "gov_letter", "other"]
    jurisdiction: str
    plain_summary: str
    extracted_facts: list[ExtractedFact]
    claims: list[Claim]
    verification: list[Verification]   # the centerpiece — document vs rule
    actions: list[Action]
    disclaimer: str

class DecodeRequest(BaseModel):
    text: str
    jurisdiction: str = "IE"
```

### API surface

| Method | Path | Body / Params | Returns |
|---|---|---|---|
| `POST` | `/api/decode` | `DecodeRequest` | `DecodeResult` |
| `GET` | `/api/documents` | — | `list[DecodeResult]` (history) |
| `GET` | `/api/documents/{id}` | — | `DecodeResult` |
| `GET` | `/api/health` | — | `{status, demo_mode}` |

### SQLite schema (SQLAlchemy, `backend/app/models.py`)
`documents(id, created_at, raw_text, doc_type, jurisdiction, plain_summary)` — one row per decode. Child tables `sources`, `claims`, `verifications`, `actions` each hold a `document_id` FK. Persisted so the history endpoints and reproducibility (same doc → same stored receipts) work. Use `create_all` on startup — no migration tooling for a hackathon.

### The pipeline (six stages, `backend/app/pipeline/`)
1. **classify** `(text) → doc_type, jurisdiction` — one Qwen call.
2. **extract** `(text, doc_type) → ExtractedFact[]` — Qwen returns structured JSON; each fact carries the source span. *This is what makes it case-specific, not generic.*
3. **retrieve** `(doc_type, facts, jurisdiction) → candidate URLs` — Exa neural search for the governing rule pages (e.g. "RTB notice period termination tenancy Ireland").
4. **ground** `(urls) → passages[]` — Firecrawl each URL to clean markdown, chunk, keep url+title+retrieved_at per chunk.
5. **verify** `(facts, passages) → claims[], verifications[]` — Qwen does per-claim entailment: for each assertion in the document, find the passage that supports/contradicts it, emit a `Verification` with the statute value and a <15-word quote. *This is the defensible core — no general chat does this.*
6. **act** `(doc_type, facts, verifications) → actions[]` — Qwen drafts the appeal letter / pre-filled form text / response email citing the exact rule, plus extracted deadlines.

### External clients — every one has a mock fallback
`clients/{qwen,exa,firecrawl}.py`. Each reads its key from env. **If the key is missing OR `DEMO_MODE=1`, return canned fixtures from `backend/fixtures/` instead of calling the network.** The demo must never die on a rate limit or a flaky scrape. This is non-negotiable — build the mock path first, the live path second.

- Qwen: OpenAI-compatible Chat Completions via Alibaba Model Studio. Confirm the exact base URL and model name (`qwen-plus` / `qwen-max`) from your Model Studio dashboard, since it's tied to the hackathon credits. Use the `openai` python client pointed at that base URL.
- Exa: `/search` with `type=neural`, return top URLs.
- Firecrawl: `/scrape`, `formats=["markdown"]`.

### Env (`backend/.env.example`)
```
QWEN_API_KEY=
QWEN_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1   # verify in your dashboard
QWEN_MODEL=qwen-plus
EXA_API_KEY=
FIRECRAWL_API_KEY=
DEMO_MODE=1        # 1 = use fixtures, no network. Flip to 0 for live.
```

### Hard rules for every worker
- Frontend and backend types must stay identical. If you change the schema, change both.
- Every `Verification` and grounded `Claim` must carry a real `Source` with a short verbatim quote. No source → status `unverifiable` / verdict `cannot_determine`. **Never invent a citation.**
- Ship `DEMO_MODE` working end-to-end before wiring any live API.
- Legal-adjacent: `disclaimer` field is always populated ("Information, not legal advice"). Assert rights by quoting the source, not in our own voice.

---

## 3. The four subagent files

Drop these in `.claude/agents/`. The `description` field is what makes the master delegate correctly — it's written as a triage rule. All run on Sonnet; drop the mechanical ones to Haiku later if you want to save credits.

### `.claude/agents/backend-engineer.md`
```markdown
---
name: backend-engineer
description: Use to scaffold and edit the FastAPI backend skeleton — app setup, CORS, SQLAlchemy SQLite models, pydantic schemas, and route handlers with stubbed pipeline calls. Returns file paths created and a summary of the API surface. Does NOT implement pipeline logic or external API clients.
tools: Read, Write, Edit, Bash, Glob, Grep
model: sonnet
---
You build the FastAPI backend for the Standing project. Read CLAUDE.md first — the schema in `backend/app/schemas.py` and the API table are the contract; implement exactly those shapes, do not redesign them.

Scope:
- `app/main.py`: FastAPI app, CORS open to the Vite dev origin, include the decode router, `create_all` on startup, `/api/health` returning demo_mode from env.
- `app/db.py`: SQLAlchemy engine against `standing.db`, session dependency.
- `app/models.py`: the documents + sources + claims + verifications + actions tables per CLAUDE.md.
- `app/schemas.py`: the pydantic models exactly as specified.
- `app/routers/decode.py`: POST /api/decode calls `pipeline.run.run_decode(text, jurisdiction)` (import it; it may be a stub for now), persists the result, returns it. Plus the two history GETs.
- `requirements.txt` (fastapi, uvicorn, sqlalchemy, pydantic, python-dotenv, openai, httpx).

Leave `app/pipeline/` and `app/clients/` to the pipeline-engineer, but create `app/pipeline/run.py` with a `run_decode` stub that returns a valid DecodeResult from fixtures so the endpoint is testable immediately.

Verify with `uvicorn app.main:app` boots and `/api/health` + a fixture POST to `/api/decode` return 200. Report the API surface and any schema ambiguity back — do not silently deviate from the contract.
```

### `.claude/agents/frontend-engineer.md`
```markdown
---
name: frontend-engineer
description: Use to scaffold and build the Vite + React + Tailwind frontend — the paste box, the result view, and the citation/verification/action components. Codes against the response schema in CLAUDE.md via a typed API client that can run on mocked data. Returns component list and how to run the dev server. Does NOT touch backend or pipeline code.
tools: Read, Write, Edit, Bash, Glob, Grep
model: sonnet
---
You build the frontend for Standing. Read CLAUDE.md — mirror the pydantic schema exactly in `src/types.ts`. If the backend isn't ready, develop against a mock response imported from a local fixture so you never block on it.

Scope:
- Vite React+TS scaffold, Tailwind configured.
- `src/types.ts`: TS mirror of the contract (DecodeResult and children).
- `src/api/client.ts`: `decode(text)` → typed fetch to `/api/decode` with a `VITE_MOCK=1` path returning a local fixture.
- Components:
  - `PasteBox`: big textarea, jurisdiction hint (IE), submit + loading state.
  - `ResultView`: lays out summary → verification → claims → actions.
  - `VerificationPanel`: THE hero. Each item shows the letter's assertion vs the statute value, a mismatch/matches badge, the explanation, and the source quote as a visible "receipt" with a link. Mismatches styled loud (red), matches muted.
  - `ClaimCard`: statement + status pill + linked source quote.
  - `ActionCard`: the generated letter/email/form with a copy button; deadlines shown prominently.
- Design: clean, official-but-human, mobile-friendly. The receipt/quote and the mismatch flags are the emotional payload — make them the visual focus.

Verify `npm run dev` renders a full result from the mock fixture. Report the component tree and the exact fixture shape you consumed so it can be reconciled with the backend.
```

### `.claude/agents/pipeline-engineer.md`
```markdown
---
name: pipeline-engineer
description: Use to implement the six-stage decode pipeline (classify, extract, retrieve, ground, verify, act) and the Qwen/Exa/Firecrawl clients, each with a DEMO_MODE mock fallback. This is the product logic. Returns the pipeline entry point signature and the fixture format. Assumes the FastAPI skeleton and schemas already exist.
tools: Read, Write, Edit, Bash, Glob, Grep, WebFetch
model: sonnet
---
You implement the core logic for Standing. Read CLAUDE.md — the six stages and the DecodeResult schema are specified there; produce exactly that shape.

Build `app/clients/{qwen,exa,firecrawl}.py` FIRST, each with: real implementation reading its API key from env, AND a mock branch used when the key is absent or DEMO_MODE=1, returning canned data from `backend/fixtures/`. The mock path must produce a fully valid DecodeResult end-to-end before any live call is wired.

Then `app/pipeline/`:
- classify.py, extract.py (structured JSON facts with source spans), retrieve.py (Exa neural search for governing rule pages), ground.py (Firecrawl → clean markdown → chunks with url/title/retrieved_at), verify.py (per-claim entailment producing Claim[] and Verification[], each pinned to a passage with a <15-word verbatim quote; no passage ⇒ unverifiable/cannot_determine — never fabricate a source), act.py (draft appeal/form/email citing the exact rule + extract deadlines).
- run.py: `run_decode(text, jurisdiction) -> DecodeResult` chaining all six, resilient to any single stage failing (degrade gracefully, still return partial result).

The verify stage is the defensible core — invest there. Keep Qwen prompts strict: JSON-only output, no prose, parse safely and never trust unstructured returns. Report `run_decode`'s signature and the fixture schema so the frontend can reconcile.
```

### `.claude/agents/integration-engineer.md`
```markdown
---
name: integration-engineer
description: Use last, to wire everything together — env config, seed/demo fixtures, a one-command dev runner, an end-to-end smoke test, error handling, and the README. Ensures DEMO_MODE gives a flawless offline demo. Returns how to run and demo the app.
tools: Read, Write, Edit, Bash, Glob, Grep
model: sonnet
---
You make Standing runnable and demo-proof. Read CLAUDE.md.

Scope:
- `backend/.env.example` per CLAUDE.md; load via python-dotenv.
- `backend/fixtures/`: at least three realistic Irish demo docs and their canned DecodeResults — MUST include one defective RTB termination notice whose stated notice period is shorter than the statutory minimum, so the verification panel fires a clear MISMATCH live. This is the money demo.
- `dev.sh`: boots FastAPI (uvicorn) and Vite together; prints both URLs.
- End-to-end smoke test: with DEMO_MODE=1, POST the defective-notice fixture and assert the response contains a `verification` item with verdict "mismatch". This test passing = the demo is safe.
- CORS/proxy so frontend reaches backend in dev.
- README: what it is, the "vs just ChatGPT" pitch (extraction + live grounding + verification + generated action, with per-claim receipts), setup, and `DEMO_MODE` explanation.

Verify a clean checkout runs the full flow offline (DEMO_MODE=1) end to end. Report the exact demo script: what to paste, what the audience sees.
```

---

## 4. Master execution runbook

Run these as prompts to your Sonnet main session, in order. Gate each phase on its acceptance check before moving on.

**Phase 0 — master does this itself, no delegation.**
> "Read the scaffolding plan. Create the repo skeleton and write `CLAUDE.md` containing the full contract from the plan — the pydantic schema, API table, SQLite schema, six-stage pipeline spec, env vars, and hard rules. Then create the four subagent files in `.claude/agents/` from the plan. Do not implement features yet."

Then restart the session so the agents load (or create them via `/agents`).
*Gate: `CLAUDE.md` and four agent files exist; schema is frozen.*

**Phase 1 — parallel.**
> "Delegate to backend-engineer and frontend-engineer in parallel: backend-engineer builds the FastAPI skeleton + SQLite models + schemas + routes with a fixture-backed `run_decode` stub; frontend-engineer builds the Vite/React/Tailwind shell and all result components against a local mock fixture. Both code strictly to the contract in CLAUDE.md. Report back both summaries."

*Gate: `uvicorn` boots, `/api/decode` returns a fixture DecodeResult; `npm run dev` renders a full result from mock. The two fixture shapes match the schema.*

**Phase 2 — pipeline.**
> "Delegate to pipeline-engineer: implement the three clients with DEMO_MODE mock fallbacks first, then the six pipeline stages and `run.py`, wiring the real `run_decode` into the backend route. Keep it working end-to-end in DEMO_MODE throughout. Report the entry-point signature and fixture schema."

*Gate: with `DEMO_MODE=1`, a real POST through the actual pipeline (mock clients) returns a valid DecodeResult including at least one verification.*

**Phase 3 — integration.**
> "Delegate to integration-engineer: env config, the demo fixtures including the defective RTB notice, `dev.sh`, the end-to-end smoke test asserting a mismatch fires, CORS, and the README. Confirm a clean offline demo works."

*Gate: `./dev.sh` runs both servers; pasting the defective-notice fixture shows a loud MISMATCH with a cited statute quote; smoke test passes.*

**Phase 4 — go live (optional, only if credits + time).**
Flip `DEMO_MODE=0`, add real keys, test one live decode per doc type. Keep the fixture path as the demo fallback regardless — present on fixtures if the venue wifi is bad.

---

## 5. Scope cut-list (when time runs out, drop from the bottom)

1. History endpoints + persistence UI — nice, not needed to demo.
2. Live API path — demo on fixtures; `DEMO_MODE` is the safety net.
3. `act` stage polish (multiple action types) — one good generated appeal letter is enough.
4. Multiple doc types — **tenancy/RTB alone is a complete, sharp demo.** If you cut everything else, keep this.

**Never cut:** the `verify` stage and the visible source quote. That pairing — catching that the letter is unlawful and showing the receipt — is the entire reason this isn't just ChatGPT. It's the demo.

---

## 6. The 90-second demo script

1. "Every one of us has gotten an official letter we didn't fully understand and just… complied with."
2. Paste the defective RTB termination notice.
3. Result: plain summary, then the **Verification panel lights up red** — "This notice gives 28 days. Your tenancy length requires 90 by law," with the Citizens Information quote and link as the receipt.
4. Scroll to the generated appeal letter that cites the exact rule — copy button.
5. "ChatGPT explains your letter. Standing checks whether they're even allowed to send it, and hands you the response — with a citation you can show them."
