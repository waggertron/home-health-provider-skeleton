# Implementation plans

Each phase has a self-contained plan: goal, architecture sketch, ordered task list, key design notes, and a Definition of Done. Plans are written before code; tasks land in main as a series of TDD-tight commits with `make verify-all` green at every step.

All nine phases complete. Each plan now lives under [`history/`](history/);
this index is preserved as the project's per-phase changelog.

| # | Phase | Status | Plan |
|---|---|---|---|
| 1 | Foundations | ✅ complete | [history/2026-04-23-phase-1-foundations.md](history/2026-04-23-phase-1-foundations.md) |
| 2 | Core domain | ✅ complete | [history/2026-04-23-phase-2-core-domain.md](history/2026-04-23-phase-2-core-domain.md) |
| 3 | Routing & ML | ✅ complete | [history/2026-04-24-phase-3-routing-and-ml.md](history/2026-04-24-phase-3-routing-and-ml.md) |
| 4 | Real-time gateway | ✅ complete | [history/2026-04-24-phase-4-realtime.md](history/2026-04-24-phase-4-realtime.md) |
| 5 | Ops web console | ✅ complete | [history/2026-04-24-phase-5-ops-console.md](history/2026-04-24-phase-5-ops-console.md) |
| 6 | Clinician view | ✅ complete | [history/2026-04-24-phase-6-clinician-rn-app.md](history/2026-04-24-phase-6-clinician-rn-app.md) |
| 7 | Marketing site | ✅ complete | [history/2026-04-24-phase-7-marketing-site.md](history/2026-04-24-phase-7-marketing-site.md) |
| 8 | BI pipeline | ✅ complete | [history/2026-04-24-phase-8-bi-pipeline.md](history/2026-04-24-phase-8-bi-pipeline.md) |
| 9 | E2E + polish | ✅ complete | [history/2026-04-24-phase-9-e2e-polish.md](history/2026-04-24-phase-9-e2e-polish.md) |

**Project status: v1 portfolio-ready.**

See [`../architecture.md`](../architecture.md) for the system design those plans implement.

## Workflow

When a phase's roadmap row flips to ✅ as part of its docs-close commit, `git mv` the plan into `history/` and update this index in the same commit.
