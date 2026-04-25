# Phase 9: End-to-End + Polish Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

## Pivot from the original draft

The original Phase 9 sketched a Playwright scenario, a recorded demo
video, screenshots, and a CI e2e job. For a portfolio project of this
size, Playwright + native browser CI add a heavy boot/setup tax for the
same demonstrative value as a focused bash-based smoke that exercises
the same flow via the API + WS gateway. Phase 9 ships:

- **A consolidated bash-based full-stack smoke** (`ops/full-demo.sh`)
  that builds on the existing `ws-smoke.sh`: scheduler optimizes →
  schedule.optimized lands; clinician checks in → visit.status_changed
  lands; clinician sends a GPS ping → clinician.position_updated lands.
  All on a `make up` stack, no browser required.
- **CI workflow update** to make sure the existing test suites
  (Python pytest, rt-node vitest, web-ops vitest, web-marketing vitest)
  all run on push.
- **README polish** — a tight, sectioned demo flow walkthrough that
  takes a reader from `git clone` to "see the dispatcher↔clinician loop
  fire" in under five minutes. Demo accounts expanded.
- **Final architecture-doc pass** — sweep for stale references, add a
  "v1 status snapshot" closing section with the current test/coverage
  numbers and live-port summary.
- **Plan moved to history**, roadmap row 9 → ✅; project marked
  "v1 portfolio-ready" in the README.

## Task list

1. **T1 — Plan rewrite (this doc).** No code.
2. **T2 — `ops/full-demo.sh` end-to-end smoke.** Layered on top of
   `ops/ws-smoke.sh` — minutes the scheduler WS, fires Optimize, asserts
   `schedule.optimized` arrives. Then logs in as `c00@westside.demo`
   (requires `--enable-clinician-login`), opens a clinician WS, picks
   one assigned visit, calls check-in, asserts `visit.status_changed`.
   Sends a position; asserts `clinician.position_updated`.
3. **T3 — CI sweep.** Read `.github/workflows/ci.yml`; ensure all four
   verify lanes run (`make verify-all`, plus `make verify-marketing` if
   not already covered). Document `make verify-all` as the local CI
   stand-in.
4. **T4 — README final polish.** Add a "Run the demo in five minutes"
   block: `git clone` → `cp .env.example .env` → `make up` →
   `seed_demo --force --enable-clinician-login` → open marketing →
   click into ops → second tab on `/clinician` → check in → see ops
   update. Expand the demo accounts table with `c00@westside.demo`.
5. **T5 — Architecture-doc closing pass.** Add a "v1 status snapshot"
   section at the end of `docs/architecture.md` listing service ports,
   test counts, coverage, and the gap-list for native Expo / Playwright.
   Roadmap row 9 → ✅.
6. **T6 — Docs close + plan to history.** Move this plan into
   `docs/plans/history/`, update index. Final commit explicitly says
   "v1 portfolio-ready".

## Out of scope (intentionally deferred)

- Playwright e2e suite (replaced by the bash smoke).
- Recorded demo video / GIFs — would require recording wallclock; left
  to the project owner.
- CI matrix expansion (Node 18/20/22 etc.).

## Verification

- `make up && ops/full-demo.sh` passes end-to-end on a clean machine.
- `make verify-all` clean.
- README's "Run the demo" block reproduces the loop on a fresh checkout.
- Roadmap rows 1–9 all show ✅.
