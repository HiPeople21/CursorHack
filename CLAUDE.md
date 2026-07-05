# Standing — Bureaucracy Decoder

Paste an official document → we extract *your* specific facts, retrieve the *current* governing rule, **check whether the document is even lawful**, cite every claim to a passage, and generate the response. Not "here's what it means" — "here's what they got wrong and here's your appeal." Demo jurisdiction: Ireland (RTB, Citizens Information, gov.ie).

**Stack:** Vite + React + Tailwind frontend, FastAPI backend, SQLite. External services: Qwen (LLM), Exa (search), Firecrawl (scrape), lawyer search (mock in DEMO_MODE).

This file is the **shared contract**. Every subagent reads it automatically as project context. The schema below reflects the current codebase — if you change a shape, update both the pydantic models and the TS mirror.

---

## Repo layout

```
standing/
├── CLAUDE.md                     # this file — the contract
├── frontend/
│   ├── FRONTEND_BACKLOG.md       # frontend gaps vs backend
│   └── src/
│       ├── api/client.ts         # typed fetch, mirrors schemas.py
│       ├── types.ts              # TS mirror of the contract
│       ├── hooks/useSessions.ts  # client-side session history (localStorage)
│       ├── components/
│       │   ├── PasteBox.tsx
│       │   ├── ResultView.tsx
│       │   ├── ClaimCard.tsx
│       │   ├── VerificationPanel.tsx
│       │   ├── ActionCard.tsx
│       │   ├── Sidebar.tsx
│       │   └── ProfilePanel.tsx
│       └── App.tsx
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI app + CORS + routers
│   │   ├── db.py                 # SQLite engine/session (SQLAlchemy)
│   │   ├── models.py             # ORM tables
│   │   ├── schemas.py            # pydantic request/response — THE CONTRACT
│   │   ├── routers/
│   │   │   ├── decode.py         # POST /api/decode, history endpoints
│   │   │   ├── profile.py        # encrypted profile CRUD
│   │   │   └── lawyers.py        # standalone lawyer recommendations
│   │   ├── pipeline/
│   │   │   ├── classify.py
│   │   │   ├── identify.py
│   │   │   ├── extract.py
│   │   │   ├── retrieve.py
│   │   │   ├── ground.py
│   │   │   ├── verify.py
│   │   │   ├── act.py
│   │   │   ├── refer_lawyers.py  # eligibility heuristics + search
│   │   │   └── run.py            # orchestrates all stages
│   │   └── clients/
│   │       ├── qwen.py
│   │       ├── exa.py
│   │       ├── firecrawl.py
│   │       └── lawyer_search.py
│   ├── fixtures/
│   └── requirements.txt
├── dev.sh
└── README.md
```

---

## Core response schema (`DecodeResult`)

The TS types in `frontend/src/types.ts` MUST mirror these exactly.

```python
class Source(BaseModel):
    url: str
    title: str
    quote: str          # <15 words, verbatim from the page — the "receipt"
    retrieved_at: str   # ISO timestamp

class ExtractedFact(BaseModel):
    key: str
    value: str
    span: str | None

class Claim(BaseModel):
    statement: str
    status: Literal["supported", "contradicted", "unverifiable"]
    source: Source | None

class Verification(BaseModel):
    assertion: str
    rule_value: str
    verdict: Literal["matches", "mismatch", "cannot_determine"]
    explanation: str
    source: Source | None

class Action(BaseModel):
    title: str
    kind: Literal["letter", "form", "email", "deadline", "contact"]
    body: str
    deadline: str | None

class DecodeResult(BaseModel):
    id: str
    doc_type: Literal["tenancy", "insurance", "medical_bill", "gov_letter", "other"]
    jurisdiction: str
    plain_summary: str
    extracted_facts: list[ExtractedFact]
    claims: list[Claim]
    verification: list[Verification]
    actions: list[Action]
    disclaimer: str
```

**Lawyer referrals are NOT on `DecodeResult`.** They are returned only via `POST /api/lawyers/recommend`.

---

## Decode request / response

```python
class DecodeRequest(BaseModel):
    text: str
    jurisdiction: str | None = None   # auto-detected when omitted
    institution: UserProvidedInstitution | None = None

class DecodeResponse(BaseModel):
    status: Literal["complete", "needs_institution"]
    institution_prompt: InstitutionPrompt | None = None
    result: DecodeResult | None = None
    lawyer_referral_eligible: bool = False
    lawyer_referral_reason: str = ""
```

When institution identification fails, `status="needs_institution"` and `institution_prompt` carries suggestions. The frontend should show a popup and re-submit with `institution` set (not yet implemented — see `FRONTEND_BACKLOG.md`).

When sources are weak, `lawyer_referral_eligible=true` on a complete decode. The frontend should prompt for location and call `/api/lawyers/recommend` (not yet implemented).

---

## Lawyer referral schema (standalone)

```python
class LawyerReferral(BaseModel):
    name: str
    firm: str
    practice_area: str
    location: str
    url: str | None
    phone: str | None
    reason: str

class LawyerSearchLocation(BaseModel):
    city: str | None = None
    county: str | None = None
    jurisdiction: str | None = None

class LawyerRecommendRequest(BaseModel):
    doc_type: Literal["tenancy", "insurance", "medical_bill", "gov_letter", "other"] = "other"
    jurisdiction: str = "IE"
    location: LawyerSearchLocation | None = None
    profile_id: str | None = None
    plain_summary: str = ""
    extracted_facts: list[ExtractedFact] = []
    claims: list[Claim] = []
    verification: list[Verification] = []

class LawyerRecommendResponse(BaseModel):
    referrals: list[LawyerReferral]
    eligible: bool
    reason: str
```

---

## Profile schema (autofill — encrypted at rest)

```python
class UserProfile(BaseModel):
    id: str
    full_name: str
    email: str | None
    phone: str | None
    address_line1: str
    address_line2: str | None
    city: str
    county: str
    eircode: str | None
    date_of_birth: str | None
    pps_number: str | None
    jurisdiction: str
    extra: dict[str, str]
    created_at: str
    updated_at: str
```

`UserProfileCreate` / `UserProfileUpdate` mirror create/update payloads in `schemas.py`.

---

## API surface

| Method | Path | Body / Params | Returns |
|---|---|---|---|
| `POST` | `/api/decode` | `DecodeRequest` | `DecodeResponse` |
| `GET` | `/api/documents` | — | `list[DecodeResult]` |
| `GET` | `/api/documents/{id}` | — | `DecodeResult` |
| `POST` | `/api/lawyers/recommend` | `LawyerRecommendRequest` | `LawyerRecommendResponse` |
| `POST` | `/api/profile` | `UserProfileCreate` | `UserProfile` (201) |
| `GET` | `/api/profile/{id}` | — | `UserProfile` |
| `PUT` | `/api/profile/{id}` | `UserProfileUpdate` | `UserProfile` |
| `DELETE` | `/api/profile/{id}` | — | 204 |
| `GET` | `/api/health` | — | `{status, demo_mode, tls_enabled, profile_encryption}` |

---

## SQLite schema (SQLAlchemy)

`documents(id, created_at, raw_text, doc_type, jurisdiction, plain_summary, disclaimer)` — parent row per decode. Child tables: `sources`, `extracted_facts`, `claims`, `verifications`, `actions`. Also: `institutions`, `institution_legal_links`, `user_profiles` (encrypted PII). Use `create_all` on startup — no migration tooling.

---

## The pipeline (`backend/app/pipeline/run.py`)

1. **classify** `(text, jurisdiction_hint?) → doc_type, jurisdiction` — Qwen; infers jurisdiction when hint omitted.
2. **identify** `(text, doc_type, jurisdiction) → bodies[]` — match issuing authority; may return empty → `needs_institution`.
3. **extract** `(text, doc_type) → facts[], summary`
4. **retrieve** `(bodies, doc_type, facts, jurisdiction) → urls[]` — Exa neural search
5. **ground** `(urls) → passages[]` — Firecrawl scrape + chunk
6. **verify** `(facts, passages) → claims[], verifications[]`
7. **act** `(doc_type, facts, verifications) → actions[]`
8. **refer eligibility** — heuristic check only; sets `lawyer_referral_eligible` on `DecodeResponse`. Actual search via `/api/lawyers/recommend`.

`run_decode` degrades gracefully per stage — partial results still return.

---

## External clients — every one has a mock fallback

`clients/{qwen,exa,firecrawl,lawyer_search}.py`. **If the key is missing OR `DEMO_MODE=1`, return canned fixtures from `backend/fixtures/`.** The demo must never die on a rate limit or a flaky scrape.

---

## Env (`backend/.env.example`)

```
QWEN_API_KEY=
QWEN_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-plus
EXA_API_KEY=
FIRECRAWL_API_KEY=
DEMO_MODE=1
PROFILE_ENCRYPTION_KEY=
```

---

## Hard rules

- Frontend and backend types must stay identical for shared schemas.
- Every grounded `Claim` / `Verification` must carry a real `Source` with a short verbatim quote. No source → `unverifiable` / `cannot_determine`. **Never invent a citation.**
- Ship `DEMO_MODE` working end-to-end before wiring live APIs.
- `disclaimer` is always populated ("Information, not legal advice").
- Lawyer referrals are a separate endpoint — never embed on `DecodeResult`.
- Client-side sessions (`useSessions`) are localStorage-only; backend `/api/documents` is server history (not yet wired in UI).

---

## The money demo

A **defective RTB termination notice** with notice period shorter than statutory minimum → verification panel fires **MISMATCH** with a cited Citizens Information / RTB quote, plus a generated appeal letter. Never cut `verify` or the visible source quote.
