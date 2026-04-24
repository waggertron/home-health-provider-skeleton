# Phase 9: End-to-End + Polish Implementation Plan — DRAFT

> **Status:** Skeleton. Will be expanded into a task list when Phase 8 closes.

**Goal:** Tie the platform together with a one-shot Playwright scenario that exercises the full demo loop, plus the polish work needed to make the project portfolio-ready (demo video, README cleanup, screenshots, single-command boot).

**Architecture:**
- One Playwright scenario that:
  1. Boots `make up`.
  2. Logs in as scheduler in one browser context, clinician in another.
  3. Scheduler triggers Optimize → board updates.
  4. Scheduler reassigns visit X → both contexts see the change live.
  5. Clinician checks in → status_changed propagates to ops console map.
  6. Patient SMS link is clicked from a third context → confirmation event flows.
- Demo video recorded against this scenario.
- README + architecture polish; broken-link sweep; sample `.env` curated.

**Provisional task list (to be sharpened):**
1. Playwright config + base fixtures (multi-context).
2. Scenario implementation.
3. Demo video script + recording (asciicast or screen recording).
4. README screenshots + GIFs.
5. Final architecture-doc pass.
6. CI gains the e2e job (gated behind a label or nightly).

**Phase 9 DoD (sketch):**
- `make e2e` runs the scenario against `make up` and exits 0 on a clean machine.
- README has one demo video (link or embedded) + at least three screenshots.
- Roadmap row flips to ✅; project marked "v1 portfolio-ready".
