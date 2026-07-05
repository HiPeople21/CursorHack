# Standing — Bureaucracy Decoder

Paste an official document → we extract *your* specific facts, retrieve the *current* governing rule, **check whether the document is even lawful**, cite every claim to a passage, and generate the response. Not "here's what it means" — "here's what they got wrong and here's your appeal." Demo jurisdiction: Ireland (RTB, Citizens Information, gov.ie).

**Stack:** Vite + React + Tailwind frontend, FastAPI backend, SQLite. External services: Qwen (LLM), Exa (search), Firecrawl (scrape).

This file is the **shared contract**. Every subagent reads it automatically as project context. The schema below is frozen — implement exactly these shapes, do not redesign them. If you change the schema, change both the pydantic models and the TS mirror.

---

## Repo layout

```
standing/
├── CLAUDE.md                     # this file — the contract
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

## Response schema — frozen (`backend/app/schemas.py`)

The TS types in `frontend/src/types.ts` MUST mirror these exactly.

```python
# Pydantic models.

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

---

## API surface

| Method | Path | Body / Params | Returns |
|---|---|---|---|
| `POST` | `/api/decode` | `DecodeRequest` | `DecodeResult` |
| `GET` | `/api/documents` | — | `list[DecodeResult]` (history) |
| `GET` | `/api/documents/{id}` | — | `DecodeResult` |
| `GET` | `/api/health` | — | `{status, demo_mode}` |

---

## SQLite schema (SQLAlchemy, `backend/app/models.py`)

`documents(id, created_at, raw_text, doc_type, jurisdiction, plain_summary)` — one row per decode. Child tables `sources`, `claims`, `verifications`, `actions` each hold a `document_id` FK. Persisted so the history endpoints and reproducibility (same doc → same stored receipts) work. Use `create_all` on startup — no migration tooling for a hackathon.

---

## The pipeline (six stages, `backend/app/pipeline/`)

1. **classify** `(text) → doc_type, jurisdiction` — one Qwen call.
2. **extract** `(text, doc_type) → ExtractedFact[]` — Qwen returns structured JSON; each fact carries the source span. *This is what makes it case-specific, not generic.*
3. **retrieve** `(doc_type, facts, jurisdiction) → candidate URLs` — Exa neural search for the governing rule pages (e.g. "RTB notice period termination tenancy Ireland").
4. **ground** `(urls) → passages[]` — Firecrawl each URL to clean markdown, chunk, keep url+title+retrieved_at per chunk.
5. **verify** `(facts, passages) → claims[], verifications[]` — Qwen does per-claim entailment: for each assertion in the document, find the passage that supports/contradicts it, emit a `Verification` with the statute value and a <15-word quote. *This is the defensible core — no general chat does this.*
6. **act** `(doc_type, facts, verifications) → actions[]` — Qwen drafts the appeal letter / pre-filled form text / response email citing the exact rule, plus extracted deadlines.

`run.py`: `run_decode(text, jurisdiction) -> DecodeResult` chains all six, resilient to any single stage failing (degrade gracefully, still return partial result).

---

## External clients — every one has a mock fallback

`clients/{qwen,exa,firecrawl}.py`. Each reads its key from env. **If the key is missing OR `DEMO_MODE=1`, return canned fixtures from `backend/fixtures/` instead of calling the network.** The demo must never die on a rate limit or a flaky scrape. This is non-negotiable — build the mock path first, the live path second.

- **Qwen:** OpenAI-compatible Chat Completions via Alibaba Model Studio. Confirm the exact base URL and model name (`qwen-plus` / `qwen-max`) from your Model Studio dashboard, since it's tied to the hackathon credits. Use the `openai` python client pointed at that base URL.
- **Exa:** `/search` with `type=neural`, return top URLs.
- **Firecrawl:** `/scrape`, `formats=["markdown"]`.

---

## Env (`backend/.env.example`)

```
QWEN_API_KEY=
QWEN_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1   # verify in your dashboard
QWEN_MODEL=qwen-plus
EXA_API_KEY=
FIRECRAWL_API_KEY=
DEMO_MODE=1        # 1 = use fixtures, no network. Flip to 0 for live.
```

---

## Hard rules for every worker

- Frontend and backend types must stay identical. If you change the schema, change both.
- Every `Verification` and grounded `Claim` must carry a real `Source` with a short verbatim quote. No source → status `unverifiable` / verdict `cannot_determine`. **Never invent a citation.**
- Ship `DEMO_MODE` working end-to-end before wiring any live API.
- Legal-adjacent: `disclaimer` field is always populated ("Information, not legal advice"). Assert rights by quoting the source, not in our own voice.

---

## The money demo

The centerpiece is a **defective RTB termination notice** whose stated notice period is shorter than the statutory minimum, so the verification panel fires a clear **MISMATCH** with a cited Citizens Information / RTB statute quote as the receipt, plus a generated appeal letter citing the exact rule. Never cut the `verify` stage or the visible source quote — that pairing is the entire reason this isn't just ChatGPT.
