# Phase 6: Clinician View (web-first) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

## Pivot from the original draft

The original Phase 6 sketched an Expo React Native app. That's the right
production target for a real product, but for a portfolio demo it adds an
outsized amount of native-bundler tooling for the same demonstrative value.
Phase 6 ships a **web-based clinician view inside `apps/web-ops/`** instead —
same API surface, same realtime gateway, same demo loop (clinician checks in
→ ops console map updates within a second). A native Expo port stays on the
roadmap as a follow-up if/when the demo needs it; the API + JWT + WS already
support it.

## Goal

Close the dispatcher ↔ clinician feedback loop end-to-end inside one stack:
a clinician logs in, sees their day's route, checks in / out, and the
scheduler's `/today` board + map react in real time.

## Architecture

- New `apps/web-ops/app/(authed)/clinician/page.tsx` — mobile-friendly route
  view rendered when `useAuth().user.role === "clinician"`.
- A small role-aware redirect in `(authed)/layout.tsx` so a clinician landing
  on `/today` is sent to `/clinician`, and a scheduler hitting `/clinician`
  is sent back to `/today`.
- Reuses the existing API client, AuthContext, RtClient, and React Query
  setup — no new infra.

## Task list

1. **T1 — Plan rewrite + memory sync.** This file (the pivot doc). No code.
2. **T2 — Role-aware redirect + clinician route shell.** `(authed)/layout.tsx`
   gains the role redirect; `(authed)/clinician/page.tsx` renders a stub
   with a sign-out button and the user's tenant + role. Tests: layout
   redirects each role to the right place; `/clinician` shows the user's
   email.
3. **T3 — `useMyRoute` hook.** Fetches the day's visits for the logged-in
   clinician, listens for `visit.*` realtime frames to patch the cache,
   exposes the visit's status-machine helpers. Tests: cache patch on
   `visit.status_changed`, ignores frames for other tenants.
4. **T4 — ClinicianRoute UI.** `<MyRoute />` component lists each visit in
   ordering_seq sequence with status badges, patient + skill, and a primary
   action button (Check In / Check Out) that maps to the existing visit
   state-machine actions (`/visits/:id/check-in`, `/check-out`). Optimistic
   patch + 409 rollback (same pattern as `useReassignVisit`). Tests:
   renders cards in order, Check In flips status to `on_site`, 409 reverts.
5. **T5 — Position pinger.** A "Send GPS" button on the clinician page that
   POSTs `{lat, lon, ts}` to `/api/v1/positions/` using the seeded
   clinician's home coords with a small jitter, so the ops console map
   marker actually moves. Tests: button triggers a POST with the right
   payload shape; disabled-while-pending UX.
6. **T6 — Seed flag for clinician login.** Tiny addition to `seed_demo`:
   a `--enable-clinician-login` flag that sets a usable password on one
   seeded clinician account per tenant (e.g. `c00@westside.demo` /
   `demo1234`) so the smoke test + manual demo can actually log in as a
   clinician. Default off; documented in README.
7. **T7 — Docs close.** README + architecture: Phase 6 ✅, Phase 7 next.
   Move this plan into `docs/plans/history/`.

## Out of scope (deferred)

- Native Expo build, GPS background ticks, push notifications.
- Drag-to-reorder route, offline cache.
- Multi-day route view; this phase is "today" only.

## Verification

- `make verify-all` clean (Python + rt-node + web-ops vitest).
- Manual: enable clinician login via `seed_demo --force --enable-clinician-login`,
  open two browser windows: scheduler at `/today`, clinician at `/clinician`.
  Clinician taps Check In on a visit; scheduler card flips to `on_site`
  within ~1s; clinician taps Send GPS; map marker moves within ~1s.
