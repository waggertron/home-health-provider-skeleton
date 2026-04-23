# home-health-provider-skeleton

Portfolio-scale clone of [a B2B home-health platform](https://www.example.com/) — a B2B home-health dispatching platform. See [`docs/architecture.md`](docs/architecture.md) for the full design and [`docs/plans/`](docs/plans/) for phased implementation plans.

## Quick start

```bash
cp .env.example .env
make up
```

Then visit http://localhost:8000/api/v1/health.

## Local development (no Docker)

This project uses **[uv](https://github.com/astral-sh/uv)** for Python environments. Do not use `pip` or `venv` directly.

```bash
# Install uv (if not already): https://docs.astral.sh/uv/getting-started/installation/
cd apps/api
uv sync                       # creates .venv and installs deps
uv run pytest -v              # run the test suite
uv run ruff check .           # lint
```

## Demo logins

All seeded accounts use password `demo1234`.

| Email | Role | Tenant |
|---|---|---|
| `admin@westside.demo` | admin | Westside Home Health |
| `admin@sunset.demo` | admin | Sunset Hospice |

The full list (clinicians, schedulers, etc.) will appear on the ops console login screen once Phase 5 ships.

## Status

Phase 1 (Foundations) — in progress. See `docs/plans/2026-04-23-phase-1-foundations.md`.

## License

Not licensed for commercial use. Portfolio project.
