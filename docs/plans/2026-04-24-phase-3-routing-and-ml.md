# Phase 3: Routing & ML Brain Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Land the core differentiating IP — a Celery-backed job that takes a day's open visits and active clinicians for one tenant, solves the Vehicle Routing Problem with time windows and skill constraints via Google OR-Tools, and produces `RoutePlan` rows with per-clinician ordered visit sequences. Add a scikit-learn re-ranker on top of OR-Tools' cost function so the route-quality story matches the platform's pitch. Expose it behind an authenticated API endpoint.

**Architecture:**
- New `scheduling` app houses the OR-Tools adapter, the sklearn re-ranker, and the Celery task that wires them together.
- Celery worker runs in a new compose service sharing the `apps/api` Docker image.
- A `POST /api/v1/schedule/<date>/optimize` endpoint enqueues the task and returns `{job_id, status}`. Polling happens via Celery's result backend (Redis).
- `seed_demo` gains a realistic data generator: 25 clinicians × 300 patients × ~80 visits for "today" per tenant, plus 90 days of synthetic history for training the re-ranker.
- Distances use the haversine formula with a fixed 40 mph speed — known limitation documented in `docs/architecture.md`.

**Tech Stack:** Same as Phase 2, plus:
- `celery[redis]` (already a dep) + a worker service in `docker-compose.yml`.
- `ortools==9.11.*` for the VRP solver.
- `scikit-learn==1.5.*` + `numpy==1.26.*` for the re-ranker.
- No new frontends, no Node service — Phase 4 introduces the WebSocket gateway.

---

## Conventions

Same as Phase 1 + 2. Strict TDD, `make verify` gate before push, atomic commits, per-segment push.

**New permission class:** `IsSchedulerOrAdmin` already covers Phase 3 write endpoints.

---

## Task list

1. **T1 — Celery bootstrap.** `apps/api/hhps/celery.py` Celery app config. Add `worker-celery` compose service sharing the api Dockerfile. Tests: `ping.delay()` task round-trips via Redis and `result.get(timeout=5)` returns `"pong"`.
2. **T2 — `scheduling` app skeleton + distance helpers.** `apps/api/scheduling/` with `haversine(lat1, lon1, lat2, lon2) -> float` (kilometers) and `travel_seconds(km, mph=40.0) -> int`. Five tests: known-good city-pair distances, zero-distance self, antipode, fixed-speed conversion, kilometer↔mile boundary.
3. **T3 — Solver input adapter.** `scheduling/adapter.py`: `build_problem(tenant, date) -> Problem` — pulls clinicians + open visits, builds the distance matrix, returns a dataclass the solver consumes. Tests: two clinicians + five visits, verifies matrix shape and skill-constraint encoding.
4. **T4 — OR-Tools VRP solver.** `scheduling/vrp.py`: `solve(problem: Problem, time_budget_s: int = 10) -> Solution`. Handles time-window and skill constraints. Tests: a deterministic three-visit, one-clinician scenario with known-optimal route order; a skill-mismatch scenario where the LVN visit isn't assigned to the MA clinician.
5. **T5 — ML re-ranker skeleton.** `scheduling/ranker.py`: feature extraction (historical on-time %, visits-to-this-patient count, credential gap, hour-of-day, day-of-week) + `GradientBoostingRegressor` stub that loads from disk if present, else returns a constant 0.5. Tests: feature vector shape, constant-return when no model, deterministic output on a given feature vector.
6. **T6 — Synthetic history + trainer.** `scheduling/training.py`: `generate_synthetic_history(tenant, days=90)` returns a pandas-free list of tuples (visit, clinician, on_time_bool). `train_ranker(history)` fits the model and writes it to `scheduling/artifacts/ranker.pkl`. One management command `python manage.py train_ranker` wraps it. Tests: history generator deterministic under fixed seed, train call produces a pickle file and a non-constant prediction.
7. **T7 — Celery task `vrp.optimize_day`.** `scheduling/tasks.py`: loads problem, solves, writes `RoutePlan` rows, batch-updates `Visit.clinician_id` and `Visit.ordering_seq`. Uses a DB transaction per save. Tests: happy path produces exactly one `RoutePlan` per clinician with a non-empty visit list; idempotent under re-run with the same date.
8. **T8 — REST endpoint.** `POST /api/v1/schedule/<date>/optimize` returns `{job_id, status}`. Scheduler/admin only. Enqueues the Celery task. Tests: 401, 403 for clinician, 202 happy path with job_id in response. (Integration tests using Celery's `CELERY_TASK_ALWAYS_EAGER=True` config so tests don't require a running worker.)
9. **T9 — Seed expansion.** Rewrite `seed_demo` to generate 25 clinicians + 300 patients + 80 visits for today + 90 days of history per tenant, all under a fixed random seed for determinism. Tests: seeded data counts match specification; repeated idempotent runs don't double-create.
10. **T10 — Docs.** Update README + architecture.md: Phase 3 complete, new endpoint, new seed scale, ranker artifact path. Roadmap row flips to ✅.

Expected test count post-Phase 3: **~95** (73 from Phase 2 + ~22 new).

---

## Per-task shape

Same as Phase 2 — each task is a full TDD cycle (failing test → minimal impl → green full suite → commit → push). Gate: `make verify` before every push.

---

## Key design notes

### Distance matrix
- Haversine formula in plain Python. Known limitation flagged in `docs/architecture.md` §13: road network effects are absent.
- `travel_seconds(km, mph=40.0)` assumes a fixed average speed. Works fine inside LA Basin for demo purposes.

### VRP encoding
- **Nodes:** one depot per clinician (their home coords) + one node per visit.
- **Vehicles:** one per clinician.
- **Dimensions:**
  - `time` with cumulative travel + service; each visit has a time window `[window_start, window_end]`.
  - Service time is a fixed 30 min per visit for now (configurable later in model).
- **Constraints:**
  - Skill/credential: a visit node is only reachable by vehicles whose clinician's credential matches or exceeds the required skill.
  - Clinician shift windows: vehicle start/end times bounded by the clinician's shift.
- **Objective:** minimize total travel time, softly penalized by `(1 - ranker.score(visit, clinician))` so the ML model shifts assignments toward historically successful pairings.
- **Time budget:** 10s per solve. On timeout, we accept the solver's best-found solution (it still has one via the first-solution heuristic).

### Re-ranker
- Features are intentionally simple so training on synthetic data is cheap.
- Model lives at `scheduling/artifacts/ranker.pkl`. In-repo but gitignored — training is a one-shot build step.
- If the pickle is missing at solver time, the objective degenerates to pure travel-time minimization. Tests cover both paths.

### Celery config
- Dev/test runs with `CELERY_TASK_ALWAYS_EAGER=True` so we don't require a running worker for pytest.
- Production compose spins up a real `worker-celery` container.

---

## Phase 3 Definition of Done

- [ ] Celery worker boots inside compose and `vrp.optimize_day.delay(...)` executes.
- [ ] `seed_demo --force` produces 2 tenants × 25 clinicians × 300 patients × 80 today-visits × 90 days of history — in under 30 seconds.
- [ ] `POST /api/v1/schedule/<date>/optimize` returns 202 with a job_id; solver runs; RoutePlan rows appear; affected Visit rows have `clinician_id` and `ordering_seq` populated.
- [ ] Skill constraint verified by test: an RN-only visit never goes to an MA-only clinician.
- [ ] Full test suite ~95 passing.
- [ ] `make verify` clean.
- [ ] CI green on main.
- [ ] README + architecture.md updated.

---

## Handoff to Phase 4

Phase 4 (Real-time) adds the Node WebSocket gateway and Redis pub/sub fanout. The VRP task from Phase 3 will gain `PUBLISH tenant:{id}:events {"type":"schedule.optimized", ...}` after writing RoutePlans; the gateway then fans that out to connected ops-console clients. No other Phase 3 code changes for Phase 4.
