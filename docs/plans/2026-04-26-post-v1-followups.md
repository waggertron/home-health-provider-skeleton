# Post-v1 follow-ups

> **Status:** Draft. Captures the deferred work surfaced in
> [`docs/architecture.md`](../architecture.md) §21 (Open Questions) at
> v1 close (2026-04-25). None of these are blocking; each is a
> self-contained slice that can be picked up independently.

## Goal

Keep the v1 surface frozen while peeling off discrete, demo-relevant
upgrades. Each item below is sized to land as a TDD-tight commit series
on `main` with `make verify-all` green at every step.

---

## Backlog (ordered by reviewer impact, not effort)

### 1. Wire the re-ranker score into the OR-Tools objective

- **Why.** §9.3 ships the sklearn `Ranker` and the training pipeline,
  but `solve()` doesn't yet read its score. Wiring it closes the loop
  the architecture promises.
- **Shape.** Per-arc cost adjustment in `scheduling/vrp.py`: subtract
  `γ · ranker.score(features)` from the transit callback's return for
  arcs ending at a visit node, where features are precomputed per
  `(visit, clinician)` pair from the same data the adapter already
  pulls.
- **Verification.** Two solver-level pytest cases: identical problems
  with and without an artifact pickle should produce *the same set of
  visits assigned* but a *different ordering* when the re-ranker
  prefers a clinician.

### 2. Patient SMS confirmation public endpoint

- **Why.** §13.5 designs the flow but ships nothing user-facing.
  Closing it makes the SMS log demoable end-to-end (link in outbox →
  click → confirmation lands on dashboard).
- **Shape.** `GET /p/<token>` returns a minimal HTML page (visit
  window + clinician name + Confirm button); `POST /p/<token>/confirm`
  stamps `Visit.patient_confirmed_at` and publishes
  `visit.patient_confirmed`. HMAC + 72-hour TTL + single-use nonce
  table. Public — no auth, but throttled.
- **Verification.** Three pytest cases: happy-path confirm, expired
  token rejected, replay rejected.

### 3. Multi-schema OLTP/OLAP separation

- **Why.** §15 promises this but reporting tables share the default
  schema in v1. A real read-only Metabase role can't be modeled on top
  of the current setup.
- **Shape.** Migrate `reporting.*` tables into a `reporting` schema;
  add a Postgres role `metabase_ro` with `USAGE` on `reporting` and
  `SELECT` on its tables; update `bi-metabase` connection to that role.
- **Verification.** A pytest fixture asserts the role can read
  `reporting.daily_agency_stats` but not `core_visit`.

### 4. Pre-provisioned Metabase dashboards + embedded iframes

- **Why.** §15 lists eight dashboards but Metabase first-boot is
  interactive in v1. A reviewer shouldn't have to wire dashboards by
  hand.
- **Shape.** A one-shot Python sidecar `ops/metabase-bootstrap.py`
  that hits Metabase's REST API to create the database, the
  dashboards, and a signed-embed key. Add a `/reports/<slug>` route on
  `web-ops` that iframes the signed-embed URL.
- **Verification.** Manual: cold-boot `make up`, `/reports/agency`
  renders the dashboard.

### 5. Native Expo build for the clinician app

- **Why.** Decision #22 deferred this, but the clinician demo loop
  would land harder on a real phone.
- **Shape.** Reuse the `useMyRoute` / `useVisitAction` /
  `useRealtimeEvents` hooks; new RN screens for login, today's route,
  visit detail (check-in / check-out), and a background GPS pinger.
  Keep the web-first `/clinician` route intact for the lightweight
  demo.
- **Verification.** Expo Go on a phone hitting `host.docker.internal`
  exercises the full demo loop.

### 6. Playwright e2e covering UI flows

- **Why.** `ops/full-demo.sh` covers the back-end loop but not the UI.
- **Shape.** One scenario per role: dispatcher reassigns a visit and
  watches the card flip; clinician checks in and watches the map pin
  turn green. Two browser contexts in the same Playwright run.
- **Verification.** The scenario passes against `make up`.

### 7. Sentry + OTel wiring

- **Why.** §17 lists this as the production bridge.
- **Shape.** `sentry-sdk[django]` for the api lane,
  `@sentry/node` for rt-node, both gated on a `SENTRY_DSN` env var
  (no-op when unset). OTel spans on the request path and on
  `optimize_day` / `rollup_daily`. A `/metrics` endpoint on rt-node.
- **Verification.** With a self-hosted Sentry, an exception in `assign()`
  produces an event with `tenant_id`, `role`, and `visit_id` tags.

### 8. Audit log table

- **Why.** §10 promises this; no rows exist in v1.
- **Shape.** `audit_log(user_id, tenant_id, action, object_type,
  object_id, ts)` populated by a small `@audit("visit.assigned")`
  decorator on the state-machine functions.
- **Verification.** Reassigning a visit lands one row in `audit_log`
  with the expected shape.

### 9. Recorded demo video / GIFs

- **Why.** README's "Run the demo in five minutes" is the only
  demoable artifact today; a recorded walkthrough would carry the
  portfolio further.
- **Shape.** A 60–90 s screen-capture: login → today board → reassign
  → optimize → clinician view → check-in → map pin glides. Embedded
  into the README under the existing demo block.
- **Verification.** Visual.

---

## Ordering rationale

1, 2, 3 close architectural loops the README/architecture doc
explicitly promise; reviewers will look for them.
4 turns the BI claim into something visible.
5 makes the clinician story stronger but is the largest scope.
6, 7, 8 are quality / reliability moves with diminishing demo
visibility.
9 is the cherry on top once the rest are stable.

## Workflow note

When any item lands on `main`, `git mv` this file's archived form into
[`docs/plans/history/`](history/) per the repo's plan-lifecycle rule
(see `feedback_completed_phase_plans_to_history.md`).

---

*Drafted 2026-04-26 from the §21 backlog after the v1 close.*
