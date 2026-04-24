# Phase 4: Real-time Event Gateway Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fan state changes out to connected ops-console and clinician clients in under a second. Django publishes domain events to Redis; a new Node 20 + TypeScript gateway subscribes to per-tenant channels and relays JSON frames to authenticated WebSocket clients. Business logic stays in Django.

**Architecture:**
- Every Django state transition that matters for a live UI (`visit.assigned`, `visit.status_changed`, `schedule.optimized`, `sms.delivered`, `clinician.position_updated`) calls a single `core.events.publish(tenant_id, event)` helper that `PUBLISH`es to Redis channel `tenant:{id}:events`.
- New `rt-node` service (~500 LOC, TypeScript + `ws` + `ioredis`) on port 8080 accepts WS connections, authenticates each with a short-lived token minted by Django (`POST /api/v1/auth/ws-token` → 60s TTL JWT with `tenant` + `role` claims), subscribes the connection to its tenant channel, and forwards Redis messages as JSON frames.
- Heartbeats every 30s; stale connections close; clients reconnect with a fresh token.
- `CELERY_TASK_ALWAYS_EAGER` test path stays — Phase 4 tests cover the publish side in Django and the gateway side in Node independently. A small shell smoke test verifies end-to-end against a running stack.

**Tech Stack:** Phase 3 stack plus:
- `apps/rt-node/` — Node 20, TypeScript, `ws@8`, `ioredis@5`, `vitest@2`, `tsx`.
- `PyJWT` (or reuse `djangorestframework-simplejwt`) to mint the WS token from the Django side.
- No new Python deps; no new frontends.

---

## Conventions

Same as Phase 3. Strict TDD (both sides), `make verify` gate, atomic commits, per-segment push. Node side adds a sibling `make verify-node` target that runs `npm test` + `tsc --noEmit` + `eslint`.

---

## Task list

1. **T1 — `core.events.publish` helper + event schema.** `apps/api/core/events.py`: `publish(tenant_id: int, event: dict)` wraps Redis PUBLISH on channel `tenant:{id}:events`. Schema helpers: `visit_reassigned(visit)`, `visit_status_changed(visit)`, `schedule_optimized(tenant, date, summary)`, `sms_delivered(sms)`, `clinician_position_updated(position)`. Tests: publish builds correct channel + payload; schema helpers produce stable shapes; a fake Redis client verifies the PUBLISH side effect.
2. **T2 — Wire publishers into the Django write paths.** `visits/services.py` `assign`/`check_in`/`check_out`/`cancel` call `publish(...)` after DB commit. `scheduling/tasks.py::optimize_day` publishes one `schedule.optimized` summary plus per-visit `visit.reassigned` events. `clinicians/views.py::position_create` publishes `clinician.position_updated`. Tests: each service/task test asserts the correct event was published via a mocked publisher.
3. **T3 — WS-auth token endpoint.** `POST /api/v1/auth/ws-token` — authenticated scheduler/admin/clinician, returns `{token, expires_in}` with a 60-second access token carrying `tenant` + `role` claims and `scope: "ws"`. Tests: 401 unauthenticated, 200 happy path, `exp` within 60s window, `scope` claim present.
4. **T4 — Node gateway skeleton.** `apps/rt-node/` with `src/server.ts`, `src/auth.ts`, `src/redis.ts`. Accepts WS on `/ws`; first inbound frame must be `{type:"auth", token}`. Auth verifies the JWT against the shared signing key (env `JWT_SIGNING_KEY`), extracts `tenant`, rejects if `scope != "ws"` or expired. Subscribes the connection's Redis channel to `tenant:{id}:events`. Vitest unit tests for auth + channel resolution using an in-memory mock Redis.
5. **T5 — Fan-out + heartbeats.** On any subscribed channel message, parse JSON and forward to matching clients. Send `{type:"ping"}` every 30s; close sockets silent for 60s. Clean up Redis subscriptions on socket close (last-subscriber-for-channel pattern). Tests: mock Redis emits a message → client receives it; closed socket unsubscribes; silent socket gets terminated.
6. **T6 — End-to-end smoke script.** `ops/ws-smoke.sh`: logs in as `admin@westside.demo`, mints a WS token, opens a WS via `websocat`/`node scripts/ws-client.ts`, triggers `POST /schedule/<today>/optimize`, asserts a `schedule.optimized` frame arrives within 5 seconds. Runs against `make up` stack; not a pytest fixture.
7. **T7 — Compose wiring for `rt-node`.** Add `rt-node` service to `docker-compose.yml` on port 8080, sharing the Redis broker. `depends_on: cache-redis`. Build from `apps/rt-node/Dockerfile` (multi-stage Node 20-alpine). Healthcheck hits `/healthz`. README + architecture.md note updated. `make up` brings it up cleanly.
8. **T8 — Docs.** README + architecture.md: Phase 4 complete, new endpoint, new `rt-node` service, event catalog, 500ms-ish latency note. Roadmap row flips to ✅.

Expected test count post-Phase 4: **~120** Python tests + ~15 Node tests.

---

## Per-task shape

Same as Phases 2/3 — each task is a full TDD cycle (failing test → minimal impl → green full suite → commit → push). Gate: `make verify` (+ `make verify-node` from T4 onward) before every push.

---

## Key design notes

### Event envelope
```json
{
  "type": "visit.status_changed",
  "tenant_id": 1,
  "ts": "2026-04-24T18:32:11Z",
  "payload": { "visit_id": 42, "status": "on_site" }
}
```
All events share this shape. `type` is dotted (`visit.*`, `schedule.*`, `sms.*`, `clinician.*`). Clients filter on `type` prefix.

### WS auth
- Signing key shared between Django and `rt-node` via env `JWT_SIGNING_KEY` (already set for DRF SimpleJWT; re-used here).
- Client flow: login → HTTP access token → `POST /ws-token` → 60s WS token → WS connect with `{type:"auth", token}`.
- Rationale: keeps the WS gateway stateless; no DB calls in `rt-node`.

### Redis channels
- One channel per tenant: `tenant:{id}:events`. Node subscribes lazily — first client for a tenant triggers the subscription; last disconnect unsubscribes.
- Broker DB is Celery's (db=0). No conflict — `PUBLISH` is a distinct op from queue semantics.

### Heartbeats
- Server sends `{type:"ping"}` every 30s; clients respond with `{type:"pong"}`.
- Missed pong for 60s → server closes. Client handles reconnect with a fresh WS token.

### No offline buffering
- If a client misses an event while disconnected, it's gone. On reconnect, clients refetch the current state via REST. This is explicit — full event replay is Phase 5+ if ever.

---

## Phase 4 Definition of Done

- [ ] `core.events.publish` helper + event schema exists and is unit-tested.
- [ ] Every Phase 3 write path (visit state transitions, optimize_day, position create) publishes the right event.
- [ ] `POST /api/v1/auth/ws-token` returns a 60s signed token for authenticated users.
- [ ] `rt-node` boots inside compose; `/healthz` returns 200.
- [ ] End-to-end smoke test (`ops/ws-smoke.sh`) passes on `make up` stack.
- [ ] Node unit suite green; `tsc --noEmit` clean; eslint clean.
- [ ] Python test suite ~120 passing.
- [ ] `make verify` + `make verify-node` clean.
- [ ] CI green on main (CI grows a Node job).
- [ ] README + architecture.md updated.

---

## Handoff to Phase 5

Phase 5 (Ops web console) consumes this gateway directly — the Next.js app opens a WS on mount, subscribes to its tenant's events, and updates a live `TodayBoard` UI in response to `visit.*` + `schedule.*` frames. No Phase 4 code changes required for Phase 5; the event shape is the contract.
