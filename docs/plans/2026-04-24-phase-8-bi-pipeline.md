# Phase 8: BI Pipeline Implementation Plan — DRAFT

> **Status:** Skeleton. Will be expanded into a task list when Phase 7 closes.

**Goal:** Stand up a local OLTP/OLAP separation: a nightly Celery rollup populates a `reporting` Postgres schema; Metabase OSS embeds dashboards inside the ops console under `/reports/*`.

**Architecture:**
- One Postgres instance, two schemas: `core` (OLTP, Phases 1–4) and `reporting` (OLAP, this phase).
- Celery Beat task `reporting.rollup_daily` runs at 02:00 local time, reads yesterday's `core.*` activity, upserts into `reporting.daily_clinician_stats` + `reporting.daily_agency_stats`. Weekly rollup at Sunday 03:00.
- `bi-metabase` compose service points at `reporting` via a read-only Postgres role.
- Ops console embeds Metabase signed-URL iframes under `/reports`.

**Provisional task list (to be sharpened):**
1. `reporting` schema + read-only role + migrations.
2. Stats models (`DailyClinicianStats`, `DailyAgencyStats`, `WeeklyRouteEfficiency`).
3. `reporting.rollup_daily` Celery task.
4. Beat schedule wiring + lock to prevent double-run.
5. Metabase compose service + provisioning.
6. Ops console reports route with signed-URL iframes.
7. Docs close.

**Phase 8 DoD (sketch):**
- Running `python manage.py rollup --date=YYYY-MM-DD` populates the reporting tables.
- Metabase boots in compose and serves dashboards backed by the reporting schema.
- Ops console `/reports` page renders embedded dashboards via signed URLs.
- Roadmap row flips to ✅.
