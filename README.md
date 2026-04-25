# home-health-provider-skeleton

[![CI](https://github.com/waggertron/home-health-provider-skeleton/actions/workflows/ci.yml/badge.svg)](https://github.com/waggertron/home-health-provider-skeleton/actions/workflows/ci.yml)

Portfolio-scale clone of a B2B home-health dispatching platform — clinician routing, ops console, patient engagement.
Backend: **Django 5 + DRF + Postgres**. Frontends (planned): **React Native + Next.js (HeroUI)**. BI: **Metabase**.

> **Status:** Phases 1–6 complete (Foundations, Core Domain, Routing & ML, Real-time gateway, Ops web console, Clinician view). See [`docs/plans/`](docs/plans/) for the full roadmap and [`docs/architecture.md`](docs/architecture.md) for the system design (with mermaid diagrams).

## What works today

- `docker compose up -d` boots Postgres, Redis, a one-shot migrate+seed container, and the Django API.
- Seed step is **idempotent** — repeated `up` is a no-op; `make reseed` wipes and reseeds.
- JWT auth with role-scoped tokens. Tenant claim embedded in every access token.
- Multi-tenant request middleware + `TenantScopedManager` that fails closed when no tenant is in context.
- **Eight domain models** with tenant-scoped managers: Tenant, User, Clinician, Patient, Visit, RoutePlan, ClinicianPosition, SmsOutbox.
- **REST API** at `/api/v1/`:
  - `POST /auth/login`, `POST /auth/refresh` — JWT issuance.
  - `GET /health` — returns tenant name when authenticated.
  - `GET /clinicians/` + `/clinicians/:id/` — list + retrieve (scheduler/admin).
  - `GET|POST|PATCH|DELETE /patients/` — full CRUD (scheduler/admin).
  - `GET|POST|PATCH|DELETE /visits/` plus actions `/visits/:id/assign`, `/check-in`, `/check-out`, `/cancel` — the Visit state machine. Wrong-state transitions return HTTP 409 Conflict.
  - `GET /routeplans/` + `/:id/` — read-only (scheduler/admin). Writes come from the Phase 3 Celery VRP task.
  - `POST /positions/` — a clinician reports their own GPS ping (server derives clinician + tenant from JWT).
  - `GET /positions/latest/` — latest position per clinician for the ops map (scheduler/admin).
  - `GET /sms/` + `/:id/` — read-only SMS log (scheduler/admin).
  - `POST /schedule/<date>/optimize` — enqueues the OR-Tools VRP solve for a tenant/date (scheduler/admin). Returns `{job_id, status}`; Celery writes the resulting `RoutePlan` rows and stamps each affected Visit with its clinician + ordering.
- **Routing brain:** `scheduling` app houses the OR-Tools VRP adapter, the sklearn `GradientBoostingRegressor` re-ranker, and the Celery `optimize_day` task. Haversine distance matrix + 40 mph fixed-speed travel times; credential-hierarchy skill constraints; 30-min service time; 10s solve budget. Ranker artifact lives at `apps/api/scheduling/artifacts/ranker.pkl` (gitignored) — train with `python manage.py train_ranker`.
- **Dedicated Celery worker** container shares the API image. Tests run tasks inline via `CELERY_TASK_ALWAYS_EAGER=True` so CI doesn't need a live worker.
- **Real-time fanout:** state changes (`visit.reassigned`, `visit.status_changed`, `schedule.optimized`, `clinician.position_updated`) publish to `tenant:{id}:events` on Redis. A new `rt-node` TypeScript gateway (`apps/rt-node/`, ~500 LOC) on `:8080` accepts WebSocket clients at `/ws`, authenticates via a 60s JWT minted by `POST /auth/ws-token`, subscribes them to their tenant's channel, and forwards JSON frames. Heartbeats every 30s; idle sockets terminated after 60s.
- **End-to-end smoke test:** `./ops/ws-smoke.sh` logs in, mints a WS token, opens a WS, triggers an optimize, and asserts a `schedule.optimized` frame arrives within 15s.
- **Phase 3 seed scale:** `seed_demo --force` produces each tenant with 25 clinicians, 300 patients, 80 today-visits, and 90 days × 20 historical visits — deterministic under a tenant-seeded RNG.
- **Ops web console (`apps/web-ops/`)** — Next.js 16 + React 19 + HeroUI 3 + Tailwind 4 on `:3001`. JWT login, today board (visit grid grouped by clinician with status filter), one-click visit reassignment with optimistic React Query mutation + 409 rollback, an SVG live map of clinician positions, and read-only support pages (clinicians, patients, sms log). Subscribes to the rt-node WebSocket on mount and patches the visit/clinician caches as `visit.*`, `schedule.optimized`, and `clinician.position_updated` frames arrive.
- **Clinician view (Phase 6, web-first)** — same `apps/web-ops/` SPA renders a `/clinician` route when `user.role === 'clinician'`: today's visits in `ordering_seq` order, primary action button per status (Check In → on_site, Check Out → completed), and a "Send GPS" button that posts to `/positions/` so the dispatcher's map marker actually moves. The `(authed)` layout redirects each role to its right surface. `seed_demo --enable-clinician-login` flips `c00@<slug>.demo` to a usable `demo1234` password so the demo loop can be exercised end-to-end without an Expo build.
- **240+ tests** across the stack: 170 Python (pytest, 96% line coverage), 37 rt-node (vitest, 96.87%), 72 web-ops (vitest with React Testing Library + msw + a fake WebSocket).
- `ruff check`, `ruff format --check`, and `mypy` clean across the Django source; `tsc --noEmit` clean across rt-node + web-ops.
- GitHub Actions CI runs lint + typecheck + pytest on every push.

## Quick start

```bash
cp .env.example .env
make up
```

Then visit http://localhost:8000/api/v1/health and try logging in:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@westside.demo","password":"demo1234"}'
```

Smoke test the full stack end-to-end:

```bash
./ops/smoke-test.sh
```

## Demo logins

All seeded accounts use password **`demo1234`**.

| Email | Role | Tenant |
|---|---|---|
| `admin@westside.demo` | admin | Westside Home Health |
| `admin@sunset.demo` | admin | Sunset Hospice |

Seeded clinician accounts (25 per tenant, `cNN@{westside,sunset}.demo`) have unusable passwords — they exist so the VRP has bodies to assign visits to, not for login. Phase 5 will surface the full account list on the ops-console login screen.

## Local development (no Docker)

This project uses **[uv](https://github.com/astral-sh/uv)** for Python environments. Do not use `pip` or `venv` directly.

```bash
# Install uv (if not already): https://docs.astral.sh/uv/getting-started/installation/

# Postgres on localhost:5432 is required for local tests.
# Easiest: `docker compose up -d db-postgres`

cd apps/api
uv sync --extra dev           # creates .venv and installs deps
uv run pytest -v              # run the test suite
```

From the repo root, `make` targets wrap the common flows:

```bash
make up          # docker compose up + health wait
make down        # docker compose down
make reseed      # wipe + reseed demo data
make logs        # tail compose logs
make test        # uv run pytest
make lint        # ruff check + format --check
make type        # mypy across every first-party app
make fmt         # ruff format + fix
make verify      # lint + type + test — the full CI sequence locally
```

## Project layout

```
apps/
└── api/              Django 5 + DRF + SimpleJWT + Celery (planned)
    ├── hhps/         project settings, urls, asgi/wsgi
    ├── tenancy/      Tenant model, middleware, TenantScopedManager
    ├── accounts/     custom User model (tenant FK, role), JWT login/refresh
    ├── core/         health endpoint, shared permissions, BaseTenantViewSet
    ├── seed/         seed_demo management command
    ├── clinicians/   Clinician + ClinicianPosition models and endpoints
    ├── patients/     Patient CRUD
    ├── visits/       Visit model + state machine (services.py) + actions
    ├── routing/      RoutePlan model + read-only endpoint
    ├── messaging/    SmsOutbox model + read-only log
    └── scheduling/   OR-Tools VRP adapter/solver, sklearn re-ranker,
                      Celery optimize_day task, POST /schedule endpoint
├── rt-node/          Node 20 + TS WebSocket gateway (Phase 4),
│                     Redis pub/sub fanout, JWT auth on connect
└── web-ops/          Next.js 16 + HeroUI 3 ops console (Phase 5),
                      today board, reassign modal, live ops map
docs/
├── architecture.md   Full system design + mermaid diagrams
└── plans/            Phased implementation plans
ops/
└── smoke-test.sh     End-to-end smoke test
.github/workflows/
└── ci.yml            Lint + typecheck + pytest on every push
docker-compose.yml    Full stack (Postgres, Redis, db-init, api)
```

## Architecture

See [`docs/architecture.md`](docs/architecture.md) for the full system design — sections for goals, stack, service topology, data model, data flows, routing/ML plans, auth, security, and dev infra, plus five mermaid diagrams (system context, service topology, boot order, domain ERD, and sequence diagrams for the four key event flows).

## Roadmap

| Phase | Status | Ends with |
|---|---|---|
| **1. Foundations** | ✅ complete | Bootable compose + JWT auth + tenancy + seed |
| **2. Core domain** | ✅ complete | Clinician/Patient/Visit/RoutePlan/ClinicianPosition/SmsOutbox + tenant-scoped CRUD + Visit state machine |
| **3. Routing & ML** | ✅ complete | OR-Tools VRP + sklearn re-ranker + Celery `optimize_day` task + `POST /schedule/<date>/optimize` endpoint |
| **4. Real-time** | ✅ complete | Node 20 + TypeScript WebSocket gateway, Redis pub/sub fanout, 60s WS-auth tokens, end-to-end smoke test |
| **5. Ops web console** | ✅ complete | Next.js 16 + HeroUI 3 dispatcher UI: today board, optimize button, click-to-reassign modal, live SVG map, support list pages |
| **6. Clinician view** | ✅ complete | Web-first `/clinician` route: today's route, check-in / check-out actions, GPS pinger. Native Expo deferred. |
| 7. Marketing site | 🔜 next | Next.js + HeroUI brand site at `:3002` |
| 5. Ops web console | planned | Next.js + HeroUI dispatcher UI |
| 6. Clinician RN app | planned | Expo + TypeScript field app |
| 7. Marketing site | planned | Next.js + HeroUI landing page |
| 8. BI pipeline | planned | Metabase + nightly rollups |
| 9. E2E & polish | planned | Playwright + demo video |

## License

Not licensed for commercial use. Portfolio project.
