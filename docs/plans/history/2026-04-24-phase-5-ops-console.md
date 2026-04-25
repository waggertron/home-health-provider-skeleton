# Phase 5: Ops Web Console Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Stand up the dispatcher's cockpit — a Next.js 14 + HeroUI ops console (`web-ops`, port 3001) that authenticates against the Django API, opens a WebSocket against `rt-node`, and renders a live "today's board" of visits with a real-time clinician map. The two demo gestures the console must nail end-to-end: (1) press **Optimize** and watch the route plan repaint as `schedule.optimized` arrives, and (2) reassign a visit by clicking and watch every connected dispatcher update.

**Architecture:**
- New `apps/web-ops/` Next.js 14 App Router project (TypeScript, HeroUI, Tailwind).
- API client wraps the existing `/api/v1/` REST surface (JWT access + refresh, role-aware fetchers).
- A WS hook subscribes to `tenant:{id}:events` via the rt-node gateway using a 60s token from `POST /auth/ws-token`. Frames mutate a normalized event-store; React Query owns server state but listens for invalidations from WS.
- Mapbox GL JS renders a tiled LA Basin view with a marker per clinician (latest position) and a pin per active visit, color-coded by status.
- One docker-compose service: `web-ops` runs `next dev -p 3001`. Production build is a follow-up.

**Tech Stack:** Phase 4 stack plus:
- `next@14`, `react@18`, `typescript@5`
- `@heroui/react@2.4.x`, `tailwindcss@3.4.x`, `framer-motion@11`
- `@tanstack/react-query@5`
- `mapbox-gl@3.x` + `react-map-gl@7`
- `vitest@2`, `@testing-library/react@16`, `jsdom`, `msw@2`, `@playwright/test@1`

---

## Conventions

Same as Phases 2–4. Strict TDD on every component or hook with logic; `make verify-web` gate before push (lint + typecheck + vitest); `make e2e` runs the Playwright smoke. Per-segment commit + push.

---

## Task list

1. **T1 — Next.js scaffold + design-system bootstrap.** `apps/web-ops/` with `next` 14 App Router, TypeScript strict, Tailwind + HeroUI provider, dark-by-default theme, eslint + vitest configs, `make verify-web` Makefile target. Tests: `vitest run` against a placeholder `<HelloOps />` component renders inside the HeroUI provider.
2. **T2 — API client + auth context.** `lib/api.ts`: typed wrappers for `POST /auth/login`, `POST /auth/refresh`, `POST /auth/ws-token`, plus a generic `apiFetch` that auto-refreshes on 401. `contexts/AuthContext.tsx`: provider that holds tokens in memory + `localStorage`, exposes `login(email, pw)` / `logout()` / `user`. Tests: msw handlers verify login flow, refresh-on-401, logout clears storage.
3. **T3 — Real-time hook.** `hooks/useRealtimeEvents.ts`: opens a WS to `NEXT_PUBLIC_RT_URL` using a freshly minted ws-token, sends `{type:"auth", token}`, dispatches each incoming `{type, payload}` frame to subscribers, replies to pings, reconnects with exponential backoff. Tests: a mocked WebSocket replays a `schedule.optimized` frame and the subscriber callback fires; reconnect path covered with fake timers.
4. **T4 — Login page + route guards.** `app/login/page.tsx` with HeroUI form, validation, error rendering. `app/(authed)/layout.tsx` redirects to `/login` when no session. Tests: invalid credentials show error; successful login redirects to `/today`.
5. **T5 — TodayBoard data layer.** `hooks/useTodayBoard.ts`: React Query fetches `/visits/?date=today` + `/clinicians/`; subscribes to `visit.*` and `schedule.optimized` events to invalidate / patch the cache without a full refetch. Tests: cache patch on `visit.reassigned`, full invalidation on `schedule.optimized`, gracefully ignores frames for other tenants.
6. **T6 — TodayBoard UI.** `app/(authed)/today/page.tsx` lists visits grouped by clinician, with HeroUI cards and a filter bar (status, skill, clinician). Includes the "Optimize Day" button that calls `POST /schedule/<today>/optimize`, shows a toast on receipt of `schedule.optimized`. Tests (RTL): filter by status hides non-matching cards; clicking Optimize fires the request and the resulting toast renders.
7. **T7 — Visit reassign action.** Card menu: "Reassign…" opens a HeroUI modal with credentialed clinicians for the visit's required skill, calls `POST /visits/:id/assign`. Optimistic update; rollback on 409. Tests: reassign happy-path updates the card; 409 reverts and surfaces the conflict.
8. **T8 — Live map.** `components/OpsMap.tsx` Mapbox GL JS centered on LA Basin. Markers from `GET /positions/latest/` plus live updates from `clinician.position_updated` events. Visit pins from the day's open visits, color by status. Tests: position frame moves the right marker; visit pin colors reflect the latest status.
9. **T9 — Read-only support pages.** `app/(authed)/clinicians`, `/patients`, `/sms`. Three list pages backed by React Query against existing endpoints. Tests: each renders rows on mount; pagination works.
10. **T10 — Compose service + Playwright smoke.** Add a `web-ops` service to `docker-compose.yml` (Next.js dev server, mounts `apps/web-ops/`). `apps/web-ops/e2e/smoke.spec.ts`: login as `admin@westside.demo`, see today board, click Optimize, assert a clinician card flips its visit count within 15s. `make e2e` runs it against the live stack. Tests count toward Phase 5 verification.
11. **T11 — Docs.** Update README + architecture.md: Phase 5 complete, the `web-ops` service, demo flows, env vars (`NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_RT_URL`, `NEXT_PUBLIC_MAPBOX_TOKEN`). Roadmap row flips to ✅.

Expected test count post-Phase 5: **~250** total — ~204 carried in (167 Py + 37 Node), plus ~30 web-ops vitest + 1 Playwright.

---

## Per-task shape

Same as Phases 2–4. Each task is a full TDD cycle (failing test → minimal impl → green full suite → commit → push). Gate: `make verify-all && make verify-web` before every push.

---

## Key design notes

### Auth & token storage
- Access token in memory; refresh token in `localStorage` (acceptable for demo). On boot, attempt refresh; on success populate context.
- WS-token minted on demand from the WS hook; expires in 60s — the hook re-mints inside the reconnect loop.

### Realtime → React Query bridge
- For most events, patch the cached row (e.g. `visit.status_changed` → `setQueryData(['visits', id], ...)`).
- For `schedule.optimized`, invalidate the today-board query so the route reorders are picked up cleanly.
- Frames whose `tenant_id` doesn't match the logged-in user's tenant are ignored as a defense-in-depth check (the gateway already scopes by channel).

### Map
- Mapbox token via `NEXT_PUBLIC_MAPBOX_TOKEN`. README documents that the demo works without the token (map renders an "add your token" placeholder).
- Clinician markers update in place; visit pins are recreated when status changes (cheap given the demo scale).

### Test strategy
- **Unit/component:** vitest + Testing Library on hooks and pure components. msw for HTTP, `WebSocket` mocked manually for WS-only paths.
- **Integration:** vitest with a real React tree + msw + a fake WS that replays envelopes.
- **E2E (Playwright):** one happy-path scenario only — login → board → optimize → see update.

### Scope guardrails
- No drag-and-drop in Phase 5 (deferred to Phase 6/7 polish if ever).
- No embedded Metabase iframes — that arrives with Phase 8.
- No clinician RN app — that's Phase 6.
- No marketing site — Phase 7.

---

## Phase 5 Definition of Done

- [ ] `apps/web-ops/` boots inside compose at http://localhost:3001 and lets `admin@westside.demo` log in with `demo1234`.
- [ ] `/today` lists today's seeded visits grouped by clinician, with status filters working.
- [ ] Pressing **Optimize Day** triggers the VRP and the board repaints when the WS frame lands.
- [ ] Manual reassignment via the UI updates the source-of-truth in Postgres and fans out a live update to other open tabs.
- [ ] The map shows clinician markers + visit pins for the current tenant.
- [ ] `make verify-web` clean (lint + tsc + vitest).
- [ ] `make e2e` passes against `make up` stack.
- [ ] CI gains a web-ops job that runs lint + typecheck + vitest on every push.
- [ ] README + architecture.md updated; roadmap row flips to ✅.

---

## Handoff to Phase 6

Phase 6 (Clinician RN app, Expo) consumes the same REST endpoints and WS gateway with a different role flavor (`clinician`). The auth context, API client patterns, and event-stream hook from Phase 5 will be ported (or, more likely, lifted into a small `apps/shared-fe/` package). No Phase 5 backend changes are required for Phase 6.
