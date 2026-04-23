# Phase 2: Core Domain Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add the operational domain models (Clinician, Patient, Visit, RoutePlan, ClinicianPosition, SmsOutbox) with tenancy-scoped CRUD endpoints, fully typed, fully tested, so Phase 3 (VRP/ML) and Phase 5 (ops web console) have a real domain to drive.

**Architecture:** Every model carries `tenant_id` and is registered on `TenantScopedManager`. DRF `ModelViewSet`s expose CRUD with per-role permission classes. Visit owns the core state machine (`scheduled → assigned → en_route → on_site → completed`). Custom actions (`/visits/:id/assign`, `/visits/:id/check-in`, `/visits/:id/check-out`) live on the Visit viewset. No VRP, no real-time, no seed expansion — those are Phase 3+.

**Tech Stack:** Same as Phase 1 (Django 5, DRF, Postgres, pytest, mypy, ruff, uv).

---

## Conventions

Same as Phase 1. TDD strictly, atomic commits, push after each task, `uv run` for everything, zero `# type: ignore`.

**Commit prefix convention** (per Phase 1 precedent):
- Model change: `feat(<app>): ...`
- API change: `feat(api): ...`
- Test-only change: `test(<app>): ...`
- Docs: `docs: ...`

---

## Task list (in execution order)

1. **T1 — `clinicians` app.** New app, `Clinician` model (OneToOne with `User` where `role=clinician`, `credentials` enum, `skills` JSONField, `home_lat/lon`, `shift_windows` JSONField), migration, 4 tests (create, credentials enum, tenant scope, __str__).
2. **T2 — `patients` app.** `Patient` model (name, phone, address, lat/lon, `required_skill`, `preferences` JSONField). Migration, 3 tests.
3. **T3 — `visits` app.** `VisitStatus` enum (`scheduled|assigned|en_route|on_site|completed|cancelled|missed`), `Visit` model with FK to Patient + nullable FK to Clinician, window_start/end, required_skill, status, check_in_at, check_out_at, ordering_seq, notes, patient_confirmed_at. Migration, 5 tests (creation, status default, window-validation, clinician-nullable, __str__).
4. **T4 — `routing` app.** `RoutePlan` model (FK Clinician, date, `visits_ordered` JSONField, `solver_metadata` JSONField). Unique `(tenant, clinician, date)`. 3 tests.
5. **T5 — Extend `clinicians` — `ClinicianPosition` model.** (lat, lon, ts, heading, speed). Indexed on `(clinician_id, ts DESC)`. 2 tests.
6. **T6 — `messaging` app — `SmsOutbox` model.** (patient_id, visit_id, template, body, status, created_at, delivered_at, inbound_reply). 3 tests.
7. **T7 — DRF viewset: Clinician.** `/api/v1/clinicians/` list+retrieve for scheduler/admin. No create via API in Phase 2 (seeded only). 4 tests: 401 unauth, list returns own-tenant only, retrieve, cross-tenant returns 404.
8. **T8 — DRF viewset: Patient.** `/api/v1/patients/` list+retrieve+create+update for scheduler/admin. 5 tests (auth + CRUD).
9. **T9 — DRF viewset: Visit.** `/api/v1/visits/` list+retrieve+create+update + custom actions `/assign`, `/check-in`, `/check-out`, `/cancel`. Status transitions validated at the service layer. 8 tests.
10. **T10 — DRF viewset: RoutePlan.** `/api/v1/routeplans/` list+retrieve for scheduler/admin. Only clinicians can retrieve their own. 4 tests.
11. **T11 — ClinicianPosition endpoints.** `POST /api/v1/positions/` (clinician posts own), `GET /api/v1/positions/latest` (ops console gets latest-per-clinician for the map). 4 tests.
12. **T12 — SmsOutbox read-only.** `GET /api/v1/sms/` list for scheduler/admin. 2 tests.
13. **T13 — Tenancy enforcement via `BaseTenantViewSet`.** Extract a shared viewset base that: requires auth, scopes queryset to current tenant, stamps `tenant_id` on create. Refactor T7–T12 onto it. Zero behavior change; one commit. Tests stay green.
14. **T14 — Permissions: `IsScheduler`, `IsClinician`, `IsOwnVisit`.** Replace role checks in views with composable DRF permission classes. Tests verify each view uses the right one.
15. **T15 — Docs.** Update `docs/architecture.md` to mark Phase 2 complete; update README roadmap and add the new endpoints to the "What works" section. Commit as `docs:`.

Expected test count after Phase 2: **~70** (22 carried over from Phase 1 + ~48 new).

---

## Per-task shape (abbreviated — one reference below; every task follows the same pattern)

```
### Task N — <summary>

**Files to create / modify:** (absolute paths)
- Create: apps/api/<app>/models.py
- Create: apps/api/<app>/tests/test_<thing>.py
- Modify: apps/api/hhps/settings.py  (INSTALLED_APPS)

**Step N.1: Write the failing tests**
(tests drive shape of model/endpoint; multiple assertions, one behavior each)

**Step N.2: `uv run pytest <path> -v` — expect RED**
(confirm failure mode: ImportError, 404, 401, etc. — not typo)

**Step N.3: Implement the minimum to pass**
(models; `makemigrations`; viewset; permissions)

**Step N.4: `uv run pytest -q` — expect GREEN (full suite)**

**Step N.5: `uv run ruff check . && uv run ruff format --check . && uv run mypy hhps ...` — expect clean**

**Step N.6: Commit + push.**
```

Every task closes with a push so the remote always mirrors green state.

---

## Task 1 — `clinicians` app & Clinician model (fully spelled-out, for reference)

**Files:**
- Create: `apps/api/clinicians/__init__.py` (empty)
- Create: `apps/api/clinicians/apps.py` (AppConfig)
- Create: `apps/api/clinicians/models.py`
- Create: `apps/api/clinicians/tests/__init__.py` (empty)
- Create: `apps/api/clinicians/tests/test_clinician_model.py`
- Modify: `apps/api/hhps/settings.py` — add `"clinicians"` to INSTALLED_APPS.

**Failing tests (Step 1.1):**

```python
# apps/api/clinicians/tests/test_clinician_model.py
import pytest
from clinicians.models import Clinician, Credential
from accounts.models import Role, User
from tenancy.models import Tenant


@pytest.mark.django_db
def test_clinician_is_linked_to_a_user_and_tenant():
    tenant = Tenant.objects.create(name="Westside", timezone="UTC")
    user = User.objects.create_user(
        email="rn@x.demo", password="p", tenant=tenant, role=Role.CLINICIAN
    )
    c = Clinician.objects.create(
        user=user, tenant=tenant, credential=Credential.RN,
        home_lat=34.0, home_lon=-118.0,
    )
    assert c.tenant_id == tenant.id
    assert c.user_id == user.id
    assert str(c) == "rn@x.demo (RN)"


@pytest.mark.django_db
def test_credential_enum_accepts_standard_roles():
    tenant = Tenant.objects.create(name="T", timezone="UTC")
    for cred in (Credential.RN, Credential.LVN, Credential.MA, Credential.PHLEBOTOMIST):
        user = User.objects.create_user(
            email=f"{cred.value}@x.demo", password="p", tenant=tenant, role=Role.CLINICIAN
        )
        Clinician.objects.create(
            user=user, tenant=tenant, credential=cred, home_lat=0, home_lon=0,
        )
    assert Clinician.objects.count() == 4


@pytest.mark.django_db
def test_clinician_skills_defaults_to_empty_list():
    tenant = Tenant.objects.create(name="T", timezone="UTC")
    user = User.objects.create_user(
        email="a@x.demo", password="p", tenant=tenant, role=Role.CLINICIAN
    )
    c = Clinician.objects.create(
        user=user, tenant=tenant, credential=Credential.RN, home_lat=0, home_lon=0,
    )
    assert c.skills == []
    assert c.shift_windows == []


@pytest.mark.django_db
def test_scoped_manager_filters_clinicians_by_tenant():
    from tenancy.managers import set_current_tenant, clear_current_tenant
    t1 = Tenant.objects.create(name="T1", timezone="UTC")
    t2 = Tenant.objects.create(name="T2", timezone="UTC")
    for t in (t1, t2):
        u = User.objects.create_user(
            email=f"a-{t.id}@x.demo", password="p", tenant=t, role=Role.CLINICIAN
        )
        Clinician.objects.create(
            user=u, tenant=t, credential=Credential.RN, home_lat=0, home_lon=0,
        )
    set_current_tenant(t1)
    try:
        assert Clinician.scoped.count() == 1
    finally:
        clear_current_tenant()
```

**Step 1.3: Minimal implementation**

```python
# apps/api/clinicians/apps.py
from django.apps import AppConfig

class CliniciansConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "clinicians"
```

```python
# apps/api/clinicians/models.py
from django.db import models
from accounts.models import User
from tenancy.managers import TenantScopedManager
from tenancy.models import Tenant


class Credential(models.TextChoices):
    RN = "RN", "Registered Nurse"
    LVN = "LVN", "Licensed Vocational Nurse"
    MA = "MA", "Medical Assistant"
    PHLEBOTOMIST = "phlebotomist", "Phlebotomist"


class Clinician(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="clinician_profile")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="clinicians")
    credential = models.CharField(max_length=32, choices=Credential.choices)
    skills = models.JSONField(default=list, blank=True)
    home_lat = models.FloatField()
    home_lon = models.FloatField()
    shift_windows = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()
    scoped = TenantScopedManager()

    def __str__(self) -> str:
        return f"{self.user.email} ({self.credential})"
```

**Step 1.4+1.5: `uv run python manage.py makemigrations clinicians && uv run pytest -q && uv run mypy ... && uv run ruff check . && uv run ruff format --check .`**

**Step 1.6: Commit + push.**

```
feat(clinicians): Clinician model with user link and credential enum

One-to-one with User (role=clinician), required tenant FK, Credential
enum (RN/LVN/MA/phlebotomist), JSONField skills + shift_windows with
list defaults, home coordinates required. Registered on TenantScopedManager.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

---

## Tasks 2–14 (abbreviated, same shape)

Each task follows the same Red → Green → Format/Type/Test → Commit → Push pattern. The *content* is summarized in the top task list; the *process* is identical. A human executor (or the executing-plans subagent) treats each as a self-contained TDD cycle.

Specific notes where they deviate:

- **T3 Visit:** `VisitStatus` enum and `status` field default to `scheduled`. Validate `window_end > window_start` at the DB level via a `CheckConstraint`; test this rejects inverted windows.
- **T9 Visit viewset custom actions:**
  - `POST /visits/:id/assign {clinician_id}` → status `scheduled→assigned`, sets clinician FK. Tests: happy path, wrong-status 409, cross-tenant clinician 400.
  - `POST /visits/:id/check-in {lat, lon}` → status `assigned|en_route → on_site`, stamps `check_in_at`. Tests: happy, wrong-status 409, wrong-clinician 403.
  - `POST /visits/:id/check-out {notes}` → status `on_site → completed`, stamps `check_out_at`, writes notes.
  - `POST /visits/:id/cancel {reason}` → status `* → cancelled` except `completed`. Tests: happy, already-completed 409.
- **T13 `BaseTenantViewSet`:** lives in `apps/api/core/viewsets.py`. Subclasses set `queryset` to the model's `scoped` manager. A `perform_create` override stamps `tenant` from the request. **No new behavior tests** — this is pure refactor; the existing suite must stay green unchanged.
- **T14 Permissions:** `IsScheduler`, `IsClinician`, and `IsOwnVisit` live in `apps/api/core/permissions.py`. Replace `permission_classes` on each view to exercise the new classes; tests assert 403 when the wrong role hits each endpoint.

---

## Phase 2 Definition of Done

- [ ] Six new models exist with migrations: `Clinician`, `Patient`, `Visit`, `RoutePlan`, `ClinicianPosition`, `SmsOutbox`.
- [ ] `TenantScopedManager` is applied to every one, verified by a scope test.
- [ ] DRF viewsets exist for all six with correct permissions and per-tenant filtering.
- [ ] Visit custom actions (`/assign`, `/check-in`, `/check-out`, `/cancel`) enforce the state machine.
- [ ] Cross-tenant access tests prove a user from tenant A gets 404 on a tenant B resource.
- [ ] Full test suite ~70 passing.
- [ ] `uv run ruff check`, `uv run ruff format --check`, and `uv run mypy hhps clinicians patients visits routing messaging tenancy accounts core seed` are all clean.
- [ ] CI green on main.
- [ ] README "What works today" lists the new endpoints; roadmap shows Phase 2 ✅.

---

## Handoff to Phase 3

Phase 3 (Routing & ML) will add a `scheduling` app that holds the OR-Tools adapter and the sklearn re-ranker. It will consume the Phase 2 domain models directly — no new migrations to the core schema — and land a Celery task `vrp.optimize_day(tenant_id, date)` with an async API endpoint `POST /api/v1/schedule/:date/optimize`.

Phase 3 will also expand `seed_demo` to generate 25 clinicians × 300 patients × 90 days of history per tenant, which is the data the ML re-ranker trains on.
