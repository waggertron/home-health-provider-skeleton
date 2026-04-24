# Implementation plans

Each phase has a self-contained plan: goal, architecture sketch, ordered task list, key design notes, and a Definition of Done. Plans are written before code; tasks land in main as a series of TDD-tight commits with `make verify-all` green at every step.

Completed plans live under [`history/`](history/) so this directory only shows what's in flight or queued.

| # | Phase | Status | Plan |
|---|---|---|---|
| 1 | Foundations | ✅ complete | [history/2026-04-23-phase-1-foundations.md](history/2026-04-23-phase-1-foundations.md) |
| 2 | Core domain | ✅ complete | [history/2026-04-23-phase-2-core-domain.md](history/2026-04-23-phase-2-core-domain.md) |
| 3 | Routing & ML | ✅ complete | [history/2026-04-24-phase-3-routing-and-ml.md](history/2026-04-24-phase-3-routing-and-ml.md) |
| 4 | Real-time gateway | ✅ complete | [history/2026-04-24-phase-4-realtime.md](history/2026-04-24-phase-4-realtime.md) |
| 5 | Ops web console | 🚧 in progress | [2026-04-24-phase-5-ops-console.md](2026-04-24-phase-5-ops-console.md) |
| 6 | Clinician RN app | draft | [2026-04-24-phase-6-clinician-rn-app.md](2026-04-24-phase-6-clinician-rn-app.md) |
| 7 | Marketing site | draft | [2026-04-24-phase-7-marketing-site.md](2026-04-24-phase-7-marketing-site.md) |
| 8 | BI pipeline | draft | [2026-04-24-phase-8-bi-pipeline.md](2026-04-24-phase-8-bi-pipeline.md) |
| 9 | E2E + polish | draft | [2026-04-24-phase-9-e2e-polish.md](2026-04-24-phase-9-e2e-polish.md) |

See [`../architecture.md`](../architecture.md) for the system design those plans implement.

## Workflow

When a phase's roadmap row flips to ✅ as part of its docs-close commit, `git mv` the plan into `history/` and update this index in the same commit.
