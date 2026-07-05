# Frontend backlog — backend features audit

Last updated: 2026-07-05 (post-merge: institution prompt + health banner + lawyer backend)

This document tracks backend capabilities vs frontend implementation. See `CLAUDE.md` for the API contract.

**Legend**

| Status | Meaning |
|--------|---------|
| ✅ Done | Frontend wired and rendering |
| 🔶 Partial | Some UI exists; gaps remain |
| ❌ Missing | Backend ready; no frontend |
| 🔧 Backend incomplete | Backend stub; frontend blocked |

---

## Summary

| Area | Backend | Frontend | Gap |
|------|---------|----------|-----|
| Core decode (`POST /api/decode`) | ✅ | ✅ | Full `DecodeResponse` flow |
| `needs_institution` prompt flow | ✅ | ✅ | Suggestions + free-text re-submit |
| Result display (summary, facts, verification, claims, actions) | ✅ | ✅ | — |
| Cursor-style sidebar + client sessions | — | ✅ | localStorage via `useSessions` |
| User profile CRUD | ✅ | ✅ | Modal: create/edit/delete, PPS masked |
| Health / demo-mode indicator | ✅ | ✅ | Banner when `demo_mode` |
| Jurisdiction selector (auto + IE + GB) | ✅ | ✅ | Auto-detect default |
| Lawyer referrals (`POST /api/lawyers/recommend`) | ✅ | ❌ | Location popup + referral cards |
| Lawyer eligibility flags on decode | ✅ | ❌ | `lawyer_referral_eligible` not surfaced |
| Jurisdiction mismatch flag | 🔧 | ❌ | Backend detects; no mismatch field yet |
| Server document history (`GET /api/documents`) | ✅ | 🔶 | Client fns added; sidebar uses localStorage |
| Profile autofill in generated letters | 🔧 | ❌ | `profile_id` not on `DecodeRequest` |
| Identified institutions in results | 🔧 | ❌ | Not exposed in API schema |
| TLS / HTTPS dev setup | ✅ | 🔶 | Vite proxy is HTTP-only |

---

## ✅ Already implemented

- **Sidebar + multi-session** — `Sidebar`, `useSessions` (localStorage), forest palette
- **Paste & decode** — `PasteBox` → `POST /api/decode` via full `DecodeResponse`
- **Institution prompt** — inline panel with suggestions + free-text re-submit
- **Jurisdiction selector** — Auto-detect (default), IE, GB
- **Mock mode** — `VITE_MOCK=1` serves `mocks/sampleResult.ts`
- **Result display** — `ResultView`, `VerificationPanel`, `ClaimCard`, `ActionCard`
- **Profile CRUD** — `ProfilePanel`, types in `types.ts`, API in `client.ts`, delete
- **Health banner** — demo-mode indicator in `App.tsx`
- **Disclaimer** — footer in `App.tsx`
- **History API client** — `listDocuments()`, `getDocument(id)` (not wired to sidebar)

---

## ❌ Backend ready — frontend needed

### 1. Lawyer referral flow (high priority)

**Backend:** Pipeline sets `lawyer_referral_eligible` + `lawyer_referral_reason` on complete decodes. Actual referrals via `POST /api/lawyers/recommend` with decode context + user location.

**Current behaviour:** `PasteBox` ignores eligibility flags after a successful decode.

**Tasks**

- [ ] Surface `lawyer_referral_eligible` from decode response
- [ ] Popup: "We couldn't find strong sources — where are you located?" (city/county)
- [ ] Add `recommendLawyers()` to `api/client.ts`
- [ ] Display `LawyerReferral` cards (name, firm, practice area, phone, url)
- [ ] Optional: pre-fill location from saved profile

---

### 2. Jurisdiction mismatch warning (medium priority)

**Product intent:** User may set a jurisdiction hint. Backend classifies document jurisdiction independently. UI should flag when they differ.

**Backend gap:** No `jurisdiction_hint` vs `detected_jurisdiction` fields on `DecodeResult` yet.

**Tasks**

- [ ] Backend: add mismatch fields to `DecodeResponse` or `DecodeResult`
- [ ] Frontend: warning banner when hint ≠ detected
- [ ] When auto-detect returns `UNK`, prompt user to select jurisdiction and re-decode

---

### 3. Server document history sync (medium priority)

**Backend:** `GET /api/documents`, `GET /api/documents/{id}` — SQLite persistence on every decode.

**Current behaviour:** Sidebar sessions are localStorage only; `listDocuments()` / `getDocument()` exist but are unused.

**Tasks**

- [ ] Wire sidebar to server history, or sync completed decodes after decode
- [ ] Show `created_at` (requires schema extension or list endpoint)

---

### 4. Profile autofill in letters (blocked on backend)

Helpers exist in `profile_autofill.py` but `profile_id` is not accepted on `DecodeRequest`.

**Tasks (after backend wiring)**

- [ ] Pass stored profile id with decode request
- [ ] Toggle: "Fill my details into generated letters"
- [ ] Preview which placeholders were replaced vs left blank

---

## API quick reference

| Method | Path | Frontend status |
|--------|------|-----------------|
| `POST` | `/api/decode` | ✅ |
| `GET` | `/api/documents` | 🔶 client only |
| `GET` | `/api/documents/{id}` | 🔶 client only |
| `POST` | `/api/lawyers/recommend` | ❌ |
| `GET` | `/api/health` | ✅ |
| `POST` | `/api/profile` | ✅ |
| `GET` | `/api/profile/{id}` | ✅ |
| `PUT` | `/api/profile/{id}` | ✅ |
| `DELETE` | `/api/profile/{id}` | ✅ |

---

## Suggested implementation order

1. **Lawyer referral popup + cards** — completes the "can't ground it" path
2. **Jurisdiction mismatch** — needs small backend schema addition first
3. **Server history sync** — optional; sessions work for demo
4. **Profile autofill** — after backend accepts `profile_id` on decode

---

## Files to touch

| File | Purpose |
|------|---------|
| `src/types.ts` | Keep synced with `schemas.py` |
| `src/api/client.ts` | `recommendLawyers()`, history wiring |
| `src/components/ResultView.tsx` | Lawyer referrals, mismatch banner |
| New: `LawyerReferralModal.tsx` | Location prompt + results |
