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

### 1. Wire the re-ranker score into the OR-Tools objective ✅ (2026-04-26)

- **Shipped.** `Problem.rerank_costs` field; `scheduling/rerank.py:build_rerank_costs`
  returns a `[v_idx][c_idx]` matrix of integer "seconds saved" biases;
  `vrp.solve` registers per-vehicle arc cost evaluators when set
  (time-dimension callback unchanged); `optimize_day` attaches the
  matrix only when the pickle artifact is loaded.
- **Tests.** `test_vrp_rerank.py` (3) + `test_rerank.py` (3) — bias
  picks vehicle A, inverted bias picks vehicle B, None preserves
  legacy behavior; helper zero-fills disallowed pairings; helper
  scales linearly with `gamma`.

### 2. Patient SMS confirmation public endpoint ✅ (2026-04-27)

- **Shipped.** `messaging/patient_confirm.py` (Django `TimestampSigner`
  with 72-hour TTL, per-purpose salt); `messaging/public_views.py`
  with `GET /p/<token>` (HTML summary + Confirm form) and
  `POST /p/<token>/confirm` (stamps `Visit.patient_confirmed_at`,
  publishes `visit.patient_confirmed`); URLs mounted in
  `hhps/urls.py`; `core/events.py:visit_patient_confirmed` helper.
  Replay protection via the row itself — once confirmed, returns 410.
- **Tests.** `test_patient_confirm.py` (6) — happy-path GET renders
  visit, POST stamps + publishes event, replay returns 410, expired
  returns 410, malformed/tampered token returns 400.

### 3. Multi-schema OLTP/OLAP separation ✅ (2026-04-28)

- **Shipped.** Reporting migration `0002_schema_separation` creates
  the `reporting` schema, `ALTER TABLE ... SET SCHEMA reporting` moves
  `daily_clinician_stats` and `daily_agency_stats` into it (with
  `state_operations=[AlterModelTable]` so Django state tracks the
  move), and a second `RunSQL` op creates the `metabase_ro` role with
  USAGE + SELECT grants on the schema (plus `ALTER DEFAULT PRIVILEGES`
  for any future tables). Model `Meta.db_table` uses the
  `'reporting"."<name>'` trick so the ORM emits schema-qualified SQL.
  `docker-compose.yml` documents the connection hints for Metabase's
  first-boot wizard.
- **Tests.** `test_schema_separation.py` (4) — schema exists and
  holds both tables; `metabase_ro` can SELECT from reporting; cannot
  read `visits_visit` (raises `InsufficientPrivilege`); cannot INSERT
  into reporting.

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
