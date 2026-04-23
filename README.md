# home-health-provider-skeleton

[![CI](https://github.com/waggertron/home-health-provider-skeleton/actions/workflows/ci.yml/badge.svg)](https://github.com/waggertron/home-health-provider-skeleton/actions/workflows/ci.yml)

Portfolio-scale clone of [a B2B home-health platform](https://www.example.com/) — a B2B home-health dispatching platform.
Backend: **Django 5 + DRF + Postgres**. Frontends (planned): **React Native + Next.js (HeroUI)**. BI: **Metabase**.

> **Status:** Phase 1 (Foundations) complete. See [`docs/plans/`](docs/plans/) for the full roadmap and [`docs/architecture.md`](docs/architecture.md) for the system design (with mermaid diagrams).

## What works today

- `docker compose up -d` boots Postgres, Redis, a one-shot migrate+seed container, and the Django API.
- Seed step is **idempotent** — repeated `up` is a no-op; `make reseed` wipes and reseeds.
- JWT auth with role-scoped tokens. Tenant claim embedded in every access token.
- Multi-tenant request middleware + `TenantScopedManager` (fails closed when no tenant in context).
- 22 pytest tests covering models, auth, middleware, and seeding.
- GitHub Actions CI runs lint + pytest on every push.

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

The full list (clinicians, schedulers) will appear here as Phases 2–5 roll out.

## Local development (no Docker)

This project uses **[uv](https://github.com/astral-sh/uv)** for Python environments. Do not use `pip` or `venv` directly.

```bash
# Install uv (if not already): https://docs.astral.sh/uv/getting-started/installation/

# Postgres on localhost:5432 is required for local tests.
# Easiest: `docker compose up -d db-postgres`

cd apps/api
uv sync --extra dev           # creates .venv and installs deps
uv run pytest -v              # run the test suite
uv run ruff check .           # lint
uv run ruff format --check .  # format check
```

From the repo root, `make` targets wrap the common flows:

```bash
make up          # docker compose up + health wait
make down        # docker compose down
make reseed      # wipe + reseed demo data
make logs        # tail compose logs
make test        # uv run pytest
make lint        # ruff check + format --check
make fmt         # ruff format + fix
```

## Project layout

```
apps/
└── api/              Django 5 + DRF + SimpleJWT + Celery (planned)
    ├── hhps/         project settings, urls, asgi/wsgi
    ├── tenancy/      Tenant model, middleware, TenantScopedManager
    ├── accounts/     custom User model (tenant FK, role), JWT login/refresh
    ├── core/         health endpoint, shared views
    └── seed/         seed_demo management command
docs/
├── architecture.md   Full system design + mermaid diagrams
└── plans/            Phased implementation plans
ops/
└── smoke-test.sh     End-to-end smoke test
.github/workflows/
└── ci.yml            Lint + pytest on every push
docker-compose.yml    Full stack (Postgres, Redis, db-init, api)
```

## Architecture

See [`docs/architecture.md`](docs/architecture.md) for the full system design — 14 sections plus five mermaid diagrams (system context, service topology, boot order, domain ERD, and sequence diagrams for the four key event flows).

## Roadmap

| Phase | Status | Ends with |
|---|---|---|
| **1. Foundations** | ✅ complete | Bootable compose + JWT auth + tenancy + seed |
| 2. Core domain | 🔜 next | Clinician, Patient, Visit, RoutePlan models + CRUD |
| 3. Routing & ML | planned | OR-Tools VRP + sklearn re-ranker |
| 4. Real-time | planned | Node WebSocket gateway + Redis pub/sub |
| 5. Ops web console | planned | Next.js + HeroUI dispatcher UI |
| 6. Clinician RN app | planned | Expo + TypeScript field app |
| 7. Marketing site | planned | Next.js + HeroUI landing page |
| 8. BI pipeline | planned | Metabase + nightly rollups |
| 9. E2E & polish | planned | Playwright + demo video |

## License

Not licensed for commercial use. Portfolio project.
