# Phase 8: BI Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

## Goal

Stand up an analytics surface alongside the operational stack: a nightly
Celery rollup populates per-day stats tables; Metabase OSS reads them and
serves dashboards.

## Pragmatic scope

The original draft sketched two Postgres schemas (`core` + `reporting`),
signed-URL iframes embedded inside the ops console, and a per-tenant
read-only role. For a portfolio demo that's an outsized amount of plumbing
relative to the demonstrative value. Phase 8 ships:

- **One schema, one Django app (`reporting`)** with `DailyClinicianStats`
  + `DailyAgencyStats` models. Tables live alongside `core.*` in the
  default Postgres schema; the OLTP/OLAP split is logical (these tables
  are populated only by the rollup task, never by request-path code) not
  physical.
- **A `rollup` management command + Celery Beat schedule** that runs at
  02:00 local each day, reads yesterday's activity, and upserts into the
  stats tables.
- **A `bi-metabase` compose service** on `:3000` pointed at the same
  Postgres instance with a read-only Postgres role limited to the
  reporting tables. Demo dashboards aren't pre-provisioned — first-boot
  Metabase setup runs interactively.
- **Embedded iframes inside the ops console** are deferred to a follow-up.
  The Metabase URL is documented and linked from the README.

## Architecture

- New `apps/api/reporting/` Django app: models, admin (none), management
  command, Celery task, Celery Beat config.
- Postgres role `metabase_ro` granted SELECT on `reporting_*` tables only;
  created by a one-shot SQL fixture run at db-init time.
- Celery Beat scheduler runs in its own compose service (`worker-beat`),
  writing the schedule lock to Redis so multi-replica deploys can't double-
  fire (single replica today; future-proofing).

## Task list

1. **T1 — Plan rewrite (this doc).** No code.
2. **T2 — Reporting app + models.** New `apps/api/reporting/`:
   `DailyClinicianStats(tenant_id, clinician_id, date, visits_completed,
   on_time_count, late_count, total_drive_seconds, total_on_site_seconds)`
   and `DailyAgencyStats(tenant_id, date, visits_completed, missed_count,
   on_time_pct, sms_sent, sms_delivered)`. Tenant-scoped managers like the
   rest of the stack. Tests: model creation + uniqueness on (tenant_id,
   clinician_id, date).
3. **T3 — Rollup logic + management command.** `reporting/rollup.py`:
   `rollup_daily(target_date, tenant_id=None)` reads yesterday's
   COMPLETED visits from `visits.Visit`, aggregates per clinician and per
   tenant, upserts via `update_or_create`. `python manage.py rollup
   --date=YYYY-MM-DD [--tenant=N]`. Tests: idempotent re-run, on-time
   computed from `check_in_at <= window_start + grace`, multi-tenant
   isolation.
4. **T4 — Celery task + Beat schedule.** `reporting.tasks.rollup_daily`
   wraps the rollup call. `CELERY_BEAT_SCHEDULE` adds an entry that fires
   every day at 02:00 local. Test: task runs the rollup with the correct
   date arg under `CELERY_TASK_ALWAYS_EAGER`.
5. **T5 — Metabase compose service.** `bi-metabase` (Metabase OSS image)
   on `:3000`, env `MB_DB_TYPE=h2` (Metabase's own metadata DB). Pointed at
   the project Postgres via a sidecar SQL init that creates the
   `metabase_ro` role + GRANT SELECT on `reporting_*`. Doc the first-boot
   setup steps in README.
6. **T6 — Docs close.** README + architecture flip Phase 8 → ✅, Phase 9
   next. Add a one-liner about how to access Metabase. Move plan to
   history.

## Out of scope

- Per-tenant Metabase row-level filtering (use Metabase's built-in
  permissions for the demo).
- Pre-provisioned dashboards (would need a Metabase init container; the
  demo expects you to click through Metabase setup once).
- Embedded iframes inside the ops console.

## Verification

- `make verify` clean (Python tests pass).
- `make up`, then `docker compose exec api-django python manage.py rollup
  --date=2026-04-24` populates `reporting_dailyclinicianstats` +
  `reporting_dailyagencystats`.
- `http://localhost:3000` boots Metabase; first-boot wizard accepts the
  Postgres connection (host `db-postgres`, user `metabase_ro`).
- Roadmap row flips to ✅.
