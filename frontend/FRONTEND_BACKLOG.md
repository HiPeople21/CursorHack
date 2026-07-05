# Frontend backlog — backend features audit

Last audited: 2026-07-05

This document tracks backend capabilities that are **fully or partially implemented** and what the frontend still needs. It is the source of truth for frontend work until items are checked off.

**Legend**

| Status | Meaning |
|--------|---------|
| ✅ Done | Frontend wired and rendering |
| 🔶 Partial | Some UI exists; gaps remain |
| ❌ Missing | Backend ready (or nearly ready); no frontend |
| 🔧 Backend incomplete | Backend stub or not wired; frontend blocked or needs API extension |

---

## Summary

| Area | Backend | Frontend | Gap |
|------|---------|----------|-----|
| Core decode (`POST /api/decode`) | ✅ | ✅ | — |
| Result display (summary, facts, verification, claims, actions) | ✅ | ✅ | Minor polish only |
| Document history | ✅ | ❌ | List + reopen past decodes |
| User profile CRUD | ✅ | ❌ | Settings form + localStorage id |
| Profile autofill in generated letters | 🔧 | ❌ | Blocked on backend wiring |
| Jurisdiction selector (GB) | ✅ | 🔶 | Only IE in dropdown |
| Health / demo-mode indicator | ✅ | ❌ | Optional banner |
| Identified institutions in results | 🔧 | ❌ | Not exposed in API schema |
| Third-level institution detection | 🔧 | ❌ | Module exists; not in pipeline |
| TLS / HTTPS dev setup | ✅ | 🔶 | Vite proxy is HTTP-only |

---

## ✅ Already implemented (no action required)

These match the frozen `DecodeResult` contract in `backend/app/schemas.py` and `frontend/src/types.ts`.

- **Paste & decode** — `PasteBox` → `POST /api/decode` via `api/client.ts`
- **Mock mode** — `VITE_MOCK=1` serves `mocks/sampleResult.ts` without backend
- **Plain summary + doc type badge** — `ResultView`
- **Extracted facts** — chips with `span` tooltip on hover
- **Verification panel** — mismatch highlighting, source receipts (`VerificationPanel`, `SourceReceipt`)
- **Claims** — status badges + citations (`ClaimCard`)
- **Actions** — kind labels, deadline display, copy-to-clipboard (`ActionCard`)
- **Disclaimer** — footer in `App.tsx`
- **Jurisdiction on decode request** — `PasteBox` sends `jurisdiction` (currently hard-coded to IE in the UI)

---

## ❌ Backend ready — frontend needed

### 1. Document history (high priority)

**Backend:** Fully implemented.

| Method | Path | Returns |
|--------|------|---------|
| `GET` | `/api/documents` | `DecodeResult[]` (newest first) |
| `GET` | `/api/documents/{id}` | `DecodeResult` |

Each decode is persisted to SQLite on `POST /api/decode`. The response already includes `id`, but the frontend discards it after render — there is no way to revisit a past decode.

**Frontend tasks**

- [ ] Add `listDocuments()` and `getDocument(id)` to `api/client.ts`
- [ ] History sidebar or list view (doc type, summary snippet, jurisdiction)
- [ ] Click a history item → load full `ResultView` via `GET /api/documents/{id}`
- [ ] Optional: URL route `/documents/:id` for shareable links
- [ ] Empty state when no history exists
- [ ] Loading and error states for history fetch

**Notes:** `created_at` exists on the `documents` table but is **not** in `DecodeResult`. If the UI needs timestamps, either extend the schema (backend + `types.ts`) or add a lightweight list endpoint — coordinate with backend before building date UI.

---

### 2. User profile CRUD (high priority)

**Backend:** Fully implemented with Fernet encryption at rest.

| Method | Path | Body | Returns |
|--------|------|------|---------|
| `POST` | `/api/profile` | `UserProfileCreate` | `UserProfile` (201) |
| `GET` | `/api/profile/{id}` | — | `UserProfile` |
| `PUT` | `/api/profile/{id}` | `UserProfileUpdate` | `UserProfile` |
| `DELETE` | `/api/profile/{id}` | — | 204 |

Schemas live in `backend/app/schemas.py` (`UserProfile`, `UserProfileCreate`, `UserProfileUpdate`). They are **not** mirrored in `frontend/src/types.ts` yet.

**Profile fields:** `full_name`, `email`, `phone`, `address_line1`, `address_line2`, `city`, `county`, `eircode`, `date_of_birth`, `pps_number`, `jurisdiction`, `extra` (key-value map).

**Frontend tasks**

- [ ] Add TypeScript types mirroring profile schemas in `types.ts`
- [ ] Add profile API functions in `api/client.ts` (`createProfile`, `getProfile`, `updateProfile`, `deleteProfile`)
- [ ] Persist returned profile `id` in `localStorage` (backend docstring recommends this)
- [ ] Profile settings page or modal (create on first visit, edit thereafter)
- [ ] Form validation for Irish address fields (eircode format, etc.)
- [ ] Sensitive-field UX: mask PPS on display, confirm before delete
- [ ] Handle 404 (stale localStorage id) → prompt to recreate profile
- [ ] Optional: link profile jurisdiction to decode jurisdiction default

**Security note:** Profile PII is encrypted server-side. For production, backend supports TLS (`SSL_KEYFILE` / `SSL_CERTFILE`). Vite dev proxy currently targets `http://localhost:8000` only — see [TLS section](#6-tls--https-dev-setup-low-priority) if profile forms ship before production infra.

---

### 3. Health / environment indicator (low–medium priority)

**Backend:** `GET /api/health` returns:

```json
{
  "status": "ok",
  "demo_mode": true,
  "tls_enabled": false,
  "profile_encryption": true
}
```

**Frontend tasks**

- [ ] Add `getHealth()` to `api/client.ts`
- [ ] Show a subtle banner when `demo_mode` is true (“Using fixture data — live search disabled”)
- [ ] Optional dev indicator for `tls_enabled` / `profile_encryption` in a settings/debug strip

Useful for demos and debugging; not blocking core flow.

---

## 🔶 Partially implemented — frontend gaps

### 4. Multi-jurisdiction support

**Backend:** Pipeline supports at least **IE** and **GB**:

- `jurisdiction.py` — normalizes `UK` → `GB`, labels for IE/GB/US/EU
- `identify.py` — IE bodies (RTB, Citizens Information) and GB bodies (TDS, HMRC)
- `body_registry.json` — seeded institutions for both IE and GB
- `classify` can override jurisdiction from document text

**Frontend:** `PasteBox` jurisdiction `<select>` only offers Ireland (`IE`).

**Frontend tasks**

- [ ] Add `GB` (United Kingdom) to jurisdiction selector
- [ ] Update sample notice copy or add a GB tenancy sample
- [ ] Verify `DOC_TYPE_LABEL` and result badges work for GB-sourced decodes
- [ ] Consider auto-detect hint: show `result.jurisdiction` when it differs from what user selected

---

### 5. Profile autofill in action letters (blocked on backend)

**Backend status:** Helpers exist in `profile_autofill.py` (`profile_placeholders`, `apply_placeholders`) but are **not wired** into:

- `pipeline/act.py` (letter generation)
- `POST /api/decode` (no `profile_id` on `DecodeRequest`)

Placeholder tokens include `[FULL_NAME]`, `[ADDRESS]`, `[EMAIL]`, `[PPS_NUMBER]`, etc.

**Frontend tasks (after backend adds `profile_id` to decode or a post-process endpoint)**

- [ ] Pass stored profile id with decode request when user has a profile
- [ ] Toggle: “Fill my details into generated letters”
- [ ] Preview which placeholders were replaced vs left blank
- [ ] Until backend wiring lands: show raw `[PLACEHOLDER]` tokens in `ActionCard` with a nudge to complete profile

**Backend prerequisite (for tracking):**

- [ ] Accept optional `profile_id` on `DecodeRequest` or apply placeholders in `act` stage
- [ ] Document which action kinds get autofill (letter/form vs contact/deadline)

---

### 6. TLS / HTTPS dev setup (low priority)

**Backend:** `generate_dev_cert.sh`, `SSL_KEYFILE`, `SSL_CERTFILE`, `FORCE_HTTPS`, CORS allows `https://localhost:5173`.

**Frontend:** `vite.config.ts` proxies `/api` → `http://localhost:8000` only.

**Frontend tasks (only if testing encrypted profile transit locally)**

- [ ] Document or script HTTPS dev server + proxy target `https://localhost:8000`
- [ ] Trust self-signed cert in browser for local dev

Not required for the core decode demo on HTTP localhost.

---

## 🔧 Backend internal / not API-exposed

These are implemented in the pipeline or database but **do not appear in `DecodeResult`**. No frontend work unless the API contract is extended.

| Feature | Location | Notes |
|---------|----------|-------|
| Institution registry | `institution_store.py`, `institution_seed.py`, SQLite `institutions` + `institution_legal_links` | Powers retrieve/ground; no public CRUD API |
| Body identification | `identify.py` | Stub keyword matcher; results not returned to client |
| Third-level institutions | `third_level_institution.py` | **Not imported** by `run.py`; dead code for now |
| Link validation / refresh | `link_validator.py`, `institution_store.py` | Background URL health; invisible to user |
| RAG passage ranking | `rag/retriever.py` | Used inside `verify`; no separate endpoint |
| Raw document text | `documents.raw_text` in DB | Not in `DecodeResult`; would need new field/endpoint to show original paste |
| Pipeline `IdentifiedBody` | `pipeline/types.py` | Internal only (`body_id`, `display_name`, `confidence`, `source_span`) |

**If product wants “Identified authority” in the UI**, backend must add e.g. `identified_bodies: IdentifiedBody[]` to `DecodeResult` (schema change + `types.ts` sync). Frontend would then show which regulator/agency was matched and the source span.

---

## Suggested implementation order

1. **Document history** — high value, backend complete, no schema changes
2. **Profile CRUD + types** — unlocks autofill later; standalone value for form-heavy actions
3. **GB jurisdiction option** — small change, expands demo surface
4. **Health / demo banner** — quick win for hackathon demos
5. **Profile autofill UX** — after backend accepts `profile_id` on decode
6. **Identified bodies in results** — requires backend schema extension first

---

## API quick reference (frontend-relevant)

| Method | Path | Frontend status |
|--------|------|-----------------|
| `POST` | `/api/decode` | ✅ `decode()` |
| `GET` | `/api/documents` | ❌ |
| `GET` | `/api/documents/{id}` | ❌ |
| `GET` | `/api/health` | ❌ |
| `POST` | `/api/profile` | ❌ |
| `GET` | `/api/profile/{id}` | ❌ |
| `PUT` | `/api/profile/{id}` | ❌ |
| `DELETE` | `/api/profile/{id}` | ❌ |

---

## Files to touch (checklist)

When implementing the backlog, these are the primary frontend touchpoints:

| File | Purpose |
|------|---------|
| `src/types.ts` | Add `UserProfile*` types; any new `DecodeResult` fields |
| `src/api/client.ts` | History, health, profile endpoints |
| `src/App.tsx` | Navigation: history, profile entry, health banner |
| `src/components/PasteBox.tsx` | Jurisdiction options, optional profile toggle |
| `src/components/ResultView.tsx` | History context, identified bodies (future) |
| New: `ProfileForm.tsx` / `HistoryPanel.tsx` | Profile CRUD, document list |

---

## Keeping this doc updated

When a backend feature ships:

1. Add or move its row in the summary table
2. Check off frontend tasks
3. Note any new schema fields that require `types.ts` sync

When frontend completes an item, mark tasks `[x]` and move the section to **Already implemented**.
