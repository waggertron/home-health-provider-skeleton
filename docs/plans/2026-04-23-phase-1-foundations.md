# Phase 1: Foundations Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Stand up the minimum viable skeleton of the home-health platform — a bootable `docker compose` stack with Postgres, Redis, a Django+DRF API with multi-tenant JWT auth, a stub seed-on-startup service, and full CI — so every subsequent phase plugs into a working foundation.

**Architecture:** Monorepo layout with top-level `apps/` (one per service) and `ops/` (compose, seed scripts, CI). Phase 1 creates the Django API, the Postgres schema scaffold, the `db-init` one-shot, and the Redis cache — enough that future phases can add domain models, a Node real-time gateway, and web frontends without touching the bootstrapping.

**Tech Stack:** Python 3.12, Django 5.0, DRF 3.15, djangorestframework-simplejwt, psycopg 3, pytest-django, ruff, mypy (loose), Docker Compose v2, Postgres 16, Redis 7, GitHub Actions.

---

## Conventions Used Throughout This Plan

- **TDD strictly.** Red → Green → Refactor. Every task starts with a failing test.
- **File paths are exact and absolute-from-repo-root.**
- **Commits are atomic.** One commit per task unless explicitly bundled.
- **Commit message format:** `type(scope): summary` (Conventional Commits) — e.g. `test(api): add failing tenant middleware test`, `feat(api): enforce tenant scope`, `chore(ops): docker-compose skeleton`.
- **Co-author trailer:** every commit ends with
  ```
  Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
  ```
- **Python style:** ruff format + ruff check (configured in `pyproject.toml`). mypy in loose mode (no `strict`).
- **Python test runner:** `pytest` invoked via `make test` (which sets `DJANGO_SETTINGS_MODULE`).
- **Do not skip failing tests.** If a test fails unexpectedly, stop and diagnose.

---

## Repo Layout Established in Phase 1

```
home-health-provider-skeleton/
├── .github/workflows/ci.yml
├── .gitignore                       ← already exists
├── .env.example
├── Makefile
├── README.md                        ← created in this phase
├── docker-compose.yml
├── pyproject.toml                   ← root tooling config
├── apps/
│   └── api/                         ← Django project
│       ├── Dockerfile
│       ├── manage.py
│       ├── pyproject.toml
│       ├── conftest.py
│       ├── pytest.ini
│       ├── hhps/                    ← Django settings package
│       │   ├── __init__.py
│       │   ├── asgi.py
│       │   ├── wsgi.py
│       │   ├── settings.py
│       │   ├── urls.py
│       │   └── celery.py
│       ├── tenancy/                 ← multi-tenant app
│       │   ├── __init__.py
│       │   ├── apps.py
│       │   ├── models.py
│       │   ├── middleware.py
│       │   ├── managers.py
│       │   └── tests/
│       ├── accounts/                ← users + auth
│       │   ├── __init__.py
│       │   ├── apps.py
│       │   ├── models.py
│       │   ├── serializers.py
│       │   ├── views.py
│       │   ├── urls.py
│       │   └── tests/
│       ├── core/                    ← health endpoint, shared code
│       │   ├── __init__.py
│       │   ├── apps.py
│       │   ├── views.py
│       │   ├── urls.py
│       │   └── tests/
│       └── seed/                    ← seed_demo management command
│           ├── __init__.py
│           ├── apps.py
│           └── management/commands/seed_demo.py
├── docs/
│   ├── architecture.md              ← already exists
│   └── plans/
│       └── 2026-04-23-phase-1-foundations.md  ← this file
└── ops/
    └── db-init/Dockerfile           ← reuses apps/api image
```

---

## Task List Overview (in execution order)

1. Root tooling: `Makefile`, `.env.example`, `pyproject.toml`, root `README.md` stub
2. Django project bootstrap (`apps/api/`) with pytest + ruff + mypy configured
3. First green test: `GET /api/v1/health` returns `{ok: true}`
4. `Tenant` model with tests
5. `User` model (custom) with `role` field + tenant FK + tests
6. Auth endpoint: `POST /api/v1/auth/login` → JWT (access + refresh) with tests
7. Auth endpoint: `POST /api/v1/auth/refresh` with tests
8. Tenant-scoping middleware with tests (extracts `tenant_id` from JWT claim)
9. `TenantScopedManager` applied to `User` + tests (cross-tenant queries return nothing)
10. Health endpoint respects auth: returns tenant name when authenticated, null otherwise; tested
11. `seed_demo --idempotent` stub command creating two tenants + one admin each; tested
12. Dockerfile for `apps/api/`
13. `docker-compose.yml` with `db-postgres`, `cache-redis`, `api-django`, `db-init` services
14. Smoke test: script that boots compose, waits for health, asserts seeded admin can log in
15. GitHub Actions CI running lint + type + tests
16. Final README for Phase 1 (how to run, creds, next phase)

Each numbered item expands to 4–7 steps below.

---

## Task 1: Root tooling scaffolding

**Files:**
- Create: `Makefile`
- Create: `.env.example`
- Create: `pyproject.toml` (root — shared ruff config)
- Create: `README.md`

**Step 1.1: Write `.env.example`**

```dotenv
# Copy to .env before running docker compose up.
POSTGRES_USER=hhps
POSTGRES_PASSWORD=hhps_dev_only
POSTGRES_DB=hhps
POSTGRES_HOST=db-postgres
POSTGRES_PORT=5432

REDIS_HOST=cache-redis
REDIS_PORT=6379

DJANGO_SECRET_KEY=dev-secret-do-not-use-in-prod
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=*

# Default password for ALL seeded demo accounts.
DEMO_PASSWORD=demo1234
```

**Step 1.2: Write root `pyproject.toml`** (shared tool configs — ruff, black-ish formatting)

```toml
[tool.ruff]
line-length = 100
target-version = "py312"
exclude = ["migrations", "node_modules", ".venv"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "DJ"]
ignore = ["E501"]  # handled by formatter

[tool.ruff.lint.isort]
known-first-party = ["hhps", "tenancy", "accounts", "core", "seed"]
```

**Step 1.3: Write `Makefile`**

```makefile
.PHONY: up down reseed logs test lint type fmt shell

up:
	docker compose up -d
	@echo "Waiting for API..."
	@until curl -sf http://localhost:8000/api/v1/health > /dev/null; do sleep 1; done
	@echo "Up. API: http://localhost:8000  Metabase: http://localhost:3000  Ops: http://localhost:3001"

down:
	docker compose down

reseed:
	docker compose run --rm db-init python manage.py seed_demo --force

logs:
	docker compose logs -f

test:
	cd apps/api && pytest -v

lint:
	cd apps/api && ruff check . && ruff format --check .

type:
	cd apps/api && mypy hhps tenancy accounts core seed

fmt:
	cd apps/api && ruff format . && ruff check --fix .

shell:
	docker compose exec api-django python manage.py shell
```

**Step 1.4: Write initial `README.md`**

```markdown
# home-health-provider-skeleton

Portfolio-scale clone of a B2B home-health platform — a B2B home-health dispatching platform.
See `docs/architecture.md` for the full design and `docs/plans/` for phased implementation.

## Quick start

1. `cp .env.example .env`
2. `make up`
3. Visit http://localhost:8000/api/v1/health

## Demo logins

All seeded accounts use password `demo1234`.

| Email | Role | Tenant |
|---|---|---|
| `admin@westside.demo` | admin | Westside Home Health |
| `admin@sunset.demo` | admin | Sunset Hospice |

Full list appears in the ops console login screen once Phase 5 ships.

## Status

Phase 1 (Foundations) — in progress.
```

**Step 1.5: Commit**

```bash
git add Makefile .env.example pyproject.toml README.md
git commit -m "chore(ops): scaffold root tooling

Adds Makefile, .env.example, shared ruff config, and initial README.
No runtime behavior yet; groundwork for Phase 1.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Django project bootstrap

**Files:**
- Create: `apps/api/manage.py`
- Create: `apps/api/pyproject.toml`
- Create: `apps/api/pytest.ini`
- Create: `apps/api/conftest.py`
- Create: `apps/api/hhps/__init__.py`
- Create: `apps/api/hhps/settings.py`
- Create: `apps/api/hhps/urls.py`
- Create: `apps/api/hhps/asgi.py`
- Create: `apps/api/hhps/wsgi.py`

**Step 2.1: Write `apps/api/pyproject.toml`**

```toml
[project]
name = "hhps-api"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "django==5.0.*",
  "djangorestframework==3.15.*",
  "djangorestframework-simplejwt==5.3.*",
  "psycopg[binary]==3.2.*",
  "python-dotenv==1.0.*",
  "redis==5.0.*",
  "celery==5.4.*",
]

[project.optional-dependencies]
dev = [
  "pytest==8.3.*",
  "pytest-django==4.9.*",
  "ruff==0.6.*",
  "mypy==1.11.*",
  "django-stubs==5.0.*",
  "djangorestframework-stubs==3.15.*",
]
```

**Step 2.2: Write `apps/api/hhps/settings.py`**

```python
import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-secret")
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    # first-party
    "tenancy",
    "accounts",
    "core",
    "seed",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "tenancy.middleware.TenantMiddleware",
]

ROOT_URLCONF = "hhps.urls"
WSGI_APPLICATION = "hhps.wsgi.application"
ASGI_APPLICATION = "hhps.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "hhps"),
        "USER": os.environ.get("POSTGRES_USER", "hhps"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "hhps_dev_only"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

AUTH_USER_MODEL = "accounts.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Los_Angeles"
USE_I18N = False
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
STATIC_URL = "static/"
```

**Step 2.3: Write `apps/api/hhps/urls.py`**

```python
from django.urls import include, path

urlpatterns = [
    path("api/v1/", include("core.urls")),
    path("api/v1/auth/", include("accounts.urls")),
]
```

**Step 2.4: Write `apps/api/pytest.ini`**

```ini
[pytest]
DJANGO_SETTINGS_MODULE = hhps.settings
python_files = tests.py test_*.py *_tests.py
addopts = --strict-markers --tb=short -ra
```

**Step 2.5: Write `apps/api/manage.py`** (standard Django boilerplate)

**Step 2.6: Commit**

```bash
git add apps/api/
git commit -m "feat(api): bootstrap Django project skeleton

Adds settings, urls, pyproject, pytest config. No endpoints yet — next
task drives the first green test.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: First green test — `GET /api/v1/health` returns `{ok: true}`

Before building tenancy, land a trivial green test to prove the test harness works.

**Files:**
- Create: `apps/api/core/apps.py`
- Create: `apps/api/core/__init__.py`
- Create: `apps/api/core/views.py`
- Create: `apps/api/core/urls.py`
- Create: `apps/api/core/tests/__init__.py`
- Create: `apps/api/core/tests/test_health.py`

**Step 3.1: Write failing test**

`apps/api/core/tests/test_health.py`:

```python
import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_health_returns_ok_without_auth():
    client = APIClient()
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True, "tenant": None}
```

**Step 3.2: Run — expect failure**

```bash
cd apps/api && pytest core/tests/test_health.py -v
```

Expected: FAIL (URL not found / app not installed).

**Step 3.3: Implement minimal endpoint**

`apps/api/core/apps.py`:
```python
from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
```

`apps/api/core/views.py`:
```python
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    return Response({"ok": True, "tenant": None})
```

`apps/api/core/urls.py`:
```python
from django.urls import path
from . import views

urlpatterns = [path("health", views.health)]
```

**Step 3.4: Run — expect pass**

```bash
pytest core/tests/test_health.py -v
```

Expected: 1 passed.

**Step 3.5: Commit**

```bash
git add apps/api/core/
git commit -m "test(api): add health endpoint with passing test

First green test — proves pytest harness + Django URL routing work.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: `Tenant` model

**Files:**
- Create: `apps/api/tenancy/__init__.py`
- Create: `apps/api/tenancy/apps.py`
- Create: `apps/api/tenancy/models.py`
- Create: `apps/api/tenancy/tests/__init__.py`
- Create: `apps/api/tenancy/tests/test_tenant_model.py`

**Step 4.1: Write failing test**

```python
# apps/api/tenancy/tests/test_tenant_model.py
import pytest
from tenancy.models import Tenant


@pytest.mark.django_db
def test_tenant_is_created_with_name_and_timezone():
    tenant = Tenant.objects.create(
        name="Westside Home Health",
        timezone="America/Los_Angeles",
    )
    assert tenant.id is not None
    assert str(tenant) == "Westside Home Health"


@pytest.mark.django_db
def test_tenant_name_is_unique():
    Tenant.objects.create(name="Westside Home Health", timezone="America/Los_Angeles")
    with pytest.raises(Exception):
        Tenant.objects.create(name="Westside Home Health", timezone="America/Los_Angeles")
```

**Step 4.2: Run — expect failure** (module not found)

**Step 4.3: Implement**

`apps/api/tenancy/apps.py`:
```python
from django.apps import AppConfig

class TenancyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tenancy"
```

`apps/api/tenancy/models.py`:
```python
from django.db import models


class Tenant(models.Model):
    name = models.CharField(max_length=200, unique=True)
    timezone = models.CharField(max_length=64, default="America/Los_Angeles")
    home_base_lat = models.FloatField(null=True, blank=True)
    home_base_lon = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name
```

**Step 4.4: Generate migration + run tests**

```bash
python manage.py makemigrations tenancy
pytest tenancy/tests/test_tenant_model.py -v
```

Expected: 2 passed.

**Step 4.5: Commit**

```bash
git add apps/api/tenancy/
git commit -m "feat(tenancy): add Tenant model with unique name

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Custom `User` model with tenant FK and role

**Files:**
- Create: `apps/api/accounts/__init__.py`
- Create: `apps/api/accounts/apps.py`
- Create: `apps/api/accounts/models.py`
- Create: `apps/api/accounts/managers.py`
- Create: `apps/api/accounts/tests/__init__.py`
- Create: `apps/api/accounts/tests/test_user_model.py`

**Step 5.1: Write failing test**

```python
# apps/api/accounts/tests/test_user_model.py
import pytest
from tenancy.models import Tenant
from accounts.models import User, Role


@pytest.mark.django_db
def test_create_user_with_tenant_and_role():
    tenant = Tenant.objects.create(name="Westside", timezone="America/Los_Angeles")
    user = User.objects.create_user(
        email="admin@westside.demo",
        password="demo1234",
        tenant=tenant,
        role=Role.ADMIN,
    )
    assert user.pk is not None
    assert user.tenant_id == tenant.id
    assert user.role == Role.ADMIN
    assert user.check_password("demo1234")
    assert user.is_active


@pytest.mark.django_db
def test_email_is_required_and_unique_within_tenant():
    tenant = Tenant.objects.create(name="W", timezone="UTC")
    User.objects.create_user(email="a@x.demo", password="p", tenant=tenant, role=Role.CLINICIAN)
    with pytest.raises(Exception):
        User.objects.create_user(email="a@x.demo", password="p", tenant=tenant, role=Role.CLINICIAN)


@pytest.mark.django_db
def test_same_email_allowed_across_tenants():
    t1 = Tenant.objects.create(name="T1", timezone="UTC")
    t2 = Tenant.objects.create(name="T2", timezone="UTC")
    User.objects.create_user(email="a@x.demo", password="p", tenant=t1, role=Role.CLINICIAN)
    User.objects.create_user(email="a@x.demo", password="p", tenant=t2, role=Role.CLINICIAN)  # ok
```

**Step 5.2: Run — expect failure**

**Step 5.3: Implement**

`apps/api/accounts/managers.py`:
```python
from django.contrib.auth.models import BaseUserManager


class UserManager(BaseUserManager):
    def create_user(self, email: str, password: str, tenant, role, **extra):
        if not email:
            raise ValueError("email required")
        email = self.normalize_email(email)
        user = self.model(email=email, tenant=tenant, role=role, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user
```

`apps/api/accounts/models.py`:
```python
from django.contrib.auth.models import AbstractBaseUser
from django.db import models
from tenancy.models import Tenant
from .managers import UserManager


class Role(models.TextChoices):
    ADMIN = "admin", "Admin"
    SCHEDULER = "scheduler", "Scheduler"
    CLINICIAN = "clinician", "Clinician"


class User(AbstractBaseUser):
    email = models.EmailField()
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="users")
    role = models.CharField(max_length=16, choices=Role.choices)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "email"], name="uniq_user_email_per_tenant"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.email} ({self.tenant.name})"
```

`apps/api/accounts/apps.py`:
```python
from django.apps import AppConfig

class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
```

**Step 5.4: Migrate + test**

```bash
python manage.py makemigrations accounts
pytest accounts/tests/test_user_model.py -v
```

Expected: 3 passed.

**Step 5.5: Commit**

```bash
git add apps/api/accounts/
git commit -m "feat(accounts): custom User model with tenant FK and role

Email uniqueness scoped per-tenant; admin/scheduler/clinician roles.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: `POST /api/v1/auth/login` returns JWT access + refresh

**Files:**
- Create: `apps/api/accounts/serializers.py`
- Create: `apps/api/accounts/views.py`
- Create: `apps/api/accounts/urls.py`
- Create: `apps/api/accounts/tests/test_login.py`

**Step 6.1: Write failing test**

```python
# apps/api/accounts/tests/test_login.py
import pytest
from rest_framework.test import APIClient
from tenancy.models import Tenant
from accounts.models import User, Role


@pytest.fixture
def admin_user(db):
    tenant = Tenant.objects.create(name="Westside", timezone="UTC")
    return User.objects.create_user(
        email="admin@westside.demo", password="demo1234", tenant=tenant, role=Role.ADMIN
    )


def test_login_returns_access_and_refresh(admin_user):
    client = APIClient()
    r = client.post(
        "/api/v1/auth/login",
        {"email": "admin@westside.demo", "password": "demo1234"},
        format="json",
    )
    assert r.status_code == 200
    body = r.json()
    assert "access" in body and "refresh" in body
    assert body["user"]["email"] == "admin@westside.demo"
    assert body["user"]["role"] == "admin"
    assert body["user"]["tenant_id"] == admin_user.tenant_id


def test_login_wrong_password_is_401(admin_user):
    client = APIClient()
    r = client.post(
        "/api/v1/auth/login",
        {"email": "admin@westside.demo", "password": "wrong"},
        format="json",
    )
    assert r.status_code == 401


def test_login_unknown_email_is_401(db):
    client = APIClient()
    r = client.post(
        "/api/v1/auth/login",
        {"email": "nobody@x.demo", "password": "x"},
        format="json",
    )
    assert r.status_code == 401
```

**Step 6.2: Run — expect failure**

**Step 6.3: Implement**

`apps/api/accounts/serializers.py`:
```python
from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    tenant_id = serializers.IntegerField()

    class Meta:
        model = User
        fields = ["id", "email", "role", "tenant_id"]


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
```

`apps/api/accounts/views.py`:
```python
from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import LoginSerializer, UserSerializer


def _issue_tokens(user):
    refresh = RefreshToken.for_user(user)
    refresh["tenant_id"] = user.tenant_id
    refresh["role"] = user.role
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    ser = LoginSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    user = authenticate(
        request, username=ser.validated_data["email"], password=ser.validated_data["password"]
    )
    if user is None:
        return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
    tokens = _issue_tokens(user)
    return Response({**tokens, "user": UserSerializer(user).data})
```

`apps/api/accounts/urls.py`:
```python
from django.urls import path
from . import views

urlpatterns = [
    path("login", views.login),
]
```

Also add to `settings.py`:
```python
AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]
```

**Step 6.4: Run tests — expect pass**

**Step 6.5: Commit**

```bash
git commit -m "feat(accounts): POST /auth/login returns JWT tokens

Tokens carry tenant_id and role as claims for downstream middleware.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: `POST /api/v1/auth/refresh`

**Files:**
- Modify: `apps/api/accounts/urls.py`
- Create: `apps/api/accounts/tests/test_refresh.py`

**Step 7.1: Write failing test**

```python
# apps/api/accounts/tests/test_refresh.py
import pytest
from rest_framework.test import APIClient
from tenancy.models import Tenant
from accounts.models import User, Role


@pytest.fixture
def login_tokens(db):
    tenant = Tenant.objects.create(name="Westside", timezone="UTC")
    User.objects.create_user(
        email="a@x.demo", password="p", tenant=tenant, role=Role.ADMIN
    )
    client = APIClient()
    r = client.post("/api/v1/auth/login", {"email": "a@x.demo", "password": "p"}, format="json")
    return r.json()


def test_refresh_returns_new_access(login_tokens):
    client = APIClient()
    r = client.post(
        "/api/v1/auth/refresh", {"refresh": login_tokens["refresh"]}, format="json"
    )
    assert r.status_code == 200
    assert "access" in r.json()


def test_refresh_invalid_token_is_401(db):
    client = APIClient()
    r = client.post("/api/v1/auth/refresh", {"refresh": "garbage"}, format="json")
    assert r.status_code == 401
```

**Step 7.2: Run — expect failure**

**Step 7.3: Implement** (use SimpleJWT's built-in view)

`apps/api/accounts/urls.py`:
```python
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path("login", views.login),
    path("refresh", TokenRefreshView.as_view()),
]
```

**Step 7.4: Run — expect pass**

**Step 7.5: Commit**

---

## Task 8: Tenant-scoping middleware

**Files:**
- Create: `apps/api/tenancy/middleware.py`
- Create: `apps/api/tenancy/tests/test_middleware.py`

**Step 8.1: Write failing test**

```python
# apps/api/tenancy/tests/test_middleware.py
import pytest
from rest_framework.test import APIClient
from tenancy.models import Tenant
from accounts.models import User, Role
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.mark.django_db
def test_request_tenant_is_set_from_jwt():
    tenant = Tenant.objects.create(name="Westside", timezone="UTC")
    user = User.objects.create_user(
        email="a@x.demo", password="p", tenant=tenant, role=Role.ADMIN
    )
    token = RefreshToken.for_user(user)
    token["tenant_id"] = tenant.id
    access = str(token.access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["tenant"] == "Westside"


@pytest.mark.django_db
def test_request_tenant_is_none_when_unauthenticated():
    client = APIClient()
    r = client.get("/api/v1/health")
    assert r.json()["tenant"] is None
```

**Step 8.2: Run — expect failure** (health still returns hardcoded null)

**Step 8.3: Implement middleware**

`apps/api/tenancy/middleware.py`:
```python
from typing import Callable

from django.http import HttpRequest, HttpResponse
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

from tenancy.models import Tenant


class TenantMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        self.jwt_auth = JWTAuthentication()

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.tenant = None  # type: ignore[attr-defined]
        header = self.jwt_auth.get_header(request)
        if header is not None:
            try:
                raw = self.jwt_auth.get_raw_token(header)
                if raw is not None:
                    token = self.jwt_auth.get_validated_token(raw)
                    tenant_id = token.get("tenant_id")
                    if tenant_id:
                        request.tenant = Tenant.objects.filter(id=tenant_id).first()  # type: ignore[attr-defined]
            except InvalidToken:
                pass
        return self.get_response(request)
```

**Step 8.4: Update health view**

`apps/api/core/views.py`:
```python
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    tenant = getattr(request, "tenant", None)
    return Response({"ok": True, "tenant": tenant.name if tenant else None})
```

**Step 8.5: Update existing health test**

`apps/api/core/tests/test_health.py` — adjust the shape expectation is already `{"ok": True, "tenant": None}` for unauthenticated (still correct).

**Step 8.6: Run all tests — expect all pass**

```bash
pytest -v
```

**Step 8.7: Commit**

```bash
git commit -m "feat(tenancy): middleware resolves tenant from JWT claim

Attaches request.tenant for downstream use. Health endpoint now returns
tenant name when the caller is authenticated.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: `TenantScopedManager` applied to `User`

**Files:**
- Create: `apps/api/tenancy/managers.py`
- Modify: `apps/api/accounts/models.py` (swap default manager)
- Create: `apps/api/tenancy/tests/test_scoped_manager.py`

**Step 9.1: Write failing test**

```python
# apps/api/tenancy/tests/test_scoped_manager.py
import pytest
from tenancy.models import Tenant
from tenancy.managers import set_current_tenant, clear_current_tenant
from accounts.models import User, Role


@pytest.mark.django_db
def test_scoped_queryset_filters_by_current_tenant():
    t1 = Tenant.objects.create(name="T1", timezone="UTC")
    t2 = Tenant.objects.create(name="T2", timezone="UTC")
    User.objects.create_user(email="a@x.demo", password="p", tenant=t1, role=Role.ADMIN)
    User.objects.create_user(email="b@x.demo", password="p", tenant=t2, role=Role.ADMIN)

    set_current_tenant(t1)
    try:
        emails = list(User.objects.values_list("email", flat=True))
        assert emails == ["a@x.demo"]
    finally:
        clear_current_tenant()


@pytest.mark.django_db
def test_unscoped_manager_returns_all_rows():
    t1 = Tenant.objects.create(name="T1", timezone="UTC")
    t2 = Tenant.objects.create(name="T2", timezone="UTC")
    User.objects.create_user(email="a@x.demo", password="p", tenant=t1, role=Role.ADMIN)
    User.objects.create_user(email="b@x.demo", password="p", tenant=t2, role=Role.ADMIN)

    # without setting current tenant, manager returns everything (safer default for
    # admin scripts and tests)
    assert User.objects.count() == 2
```

**Step 9.2: Run — expect failure**

**Step 9.3: Implement**

`apps/api/tenancy/managers.py`:
```python
from contextvars import ContextVar
from typing import Optional

from django.db import models

from tenancy.models import Tenant

_current_tenant: ContextVar[Optional[Tenant]] = ContextVar("_current_tenant", default=None)


def set_current_tenant(tenant: Optional[Tenant]) -> None:
    _current_tenant.set(tenant)


def clear_current_tenant() -> None:
    _current_tenant.set(None)


def current_tenant() -> Optional[Tenant]:
    return _current_tenant.get()


class TenantScopedQuerySet(models.QuerySet):
    def scoped(self):
        t = current_tenant()
        if t is None:
            return self
        return self.filter(tenant=t)


class TenantScopedManager(models.Manager.from_queryset(TenantScopedQuerySet)):
    def get_queryset(self):
        return super().get_queryset().scoped()
```

`apps/api/accounts/models.py` — keep `UserManager` for create_user; add scoped manager as default:

```python
# at bottom of class User
    objects = UserManager()  # existing — supports create_user()
    scoped = TenantScopedManager()
```

Also modify `TenantMiddleware` to call `set_current_tenant` / `clear_current_tenant`:

```python
def __call__(self, request: HttpRequest) -> HttpResponse:
    # ... existing JWT decode ...
    tenant_obj = request.tenant
    if tenant_obj:
        set_current_tenant(tenant_obj)
    try:
        return self.get_response(request)
    finally:
        clear_current_tenant()
```

**Step 9.4: Run all tests — expect pass**

**Step 9.5: Commit**

```bash
git commit -m "feat(tenancy): TenantScopedManager + contextvar-based scope

User.scoped filters by current tenant; middleware sets/clears per-request.
User.objects is unscoped (needed for auth backend).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: Authenticated health shows tenant name — already done in Task 8

(Verify coverage; move on.)

---

## Task 11: `seed_demo --idempotent` stub

**Files:**
- Create: `apps/api/seed/__init__.py`
- Create: `apps/api/seed/apps.py`
- Create: `apps/api/seed/management/__init__.py`
- Create: `apps/api/seed/management/commands/__init__.py`
- Create: `apps/api/seed/management/commands/seed_demo.py`
- Create: `apps/api/seed/tests/__init__.py`
- Create: `apps/api/seed/tests/test_seed_demo.py`

**Step 11.1: Write failing test**

```python
# apps/api/seed/tests/test_seed_demo.py
import pytest
from django.core.management import call_command
from tenancy.models import Tenant
from accounts.models import User


@pytest.mark.django_db
def test_seed_demo_is_idempotent():
    call_command("seed_demo", "--idempotent")
    assert Tenant.objects.count() == 2
    assert User.objects.filter(email="admin@westside.demo").exists()
    assert User.objects.filter(email="admin@sunset.demo").exists()

    # second run is a no-op
    call_command("seed_demo", "--idempotent")
    assert Tenant.objects.count() == 2
    assert User.objects.count() == 2


@pytest.mark.django_db
def test_seed_demo_force_wipes_and_reseeds():
    call_command("seed_demo", "--idempotent")
    Tenant.objects.filter(name="Westside Home Health").update(timezone="UTC")
    call_command("seed_demo", "--force")
    assert Tenant.objects.get(name="Westside Home Health").timezone == "America/Los_Angeles"


@pytest.mark.django_db
def test_seeded_admin_can_login():
    from rest_framework.test import APIClient
    call_command("seed_demo", "--idempotent")
    client = APIClient()
    r = client.post(
        "/api/v1/auth/login",
        {"email": "admin@westside.demo", "password": "demo1234"},
        format="json",
    )
    assert r.status_code == 200
```

**Step 11.2: Run — expect failure**

**Step 11.3: Implement**

`apps/api/seed/management/commands/seed_demo.py`:
```python
import os

from django.core.management.base import BaseCommand
from django.db import transaction

from tenancy.models import Tenant
from accounts.models import User, Role


DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "demo1234")

TENANTS = [
    {"name": "Westside Home Health", "timezone": "America/Los_Angeles"},
    {"name": "Sunset Hospice", "timezone": "America/Los_Angeles"},
]

ADMINS = [
    {"tenant": "Westside Home Health", "email": "admin@westside.demo"},
    {"tenant": "Sunset Hospice", "email": "admin@sunset.demo"},
]


class Command(BaseCommand):
    help = "Seed demo tenants and default accounts. Phase 1 stub."

    def add_arguments(self, parser):
        parser.add_argument("--idempotent", action="store_true")
        parser.add_argument("--force", action="store_true")

    def handle(self, *args, **opts):
        if opts["force"]:
            User.objects.all().delete()
            Tenant.objects.all().delete()

        if opts["idempotent"] and Tenant.objects.count() >= len(TENANTS):
            self.stdout.write("Already seeded — skipping (use --force to reseed).")
            return

        with transaction.atomic():
            tenants_by_name = {}
            for t in TENANTS:
                tenant, _ = Tenant.objects.update_or_create(
                    name=t["name"], defaults={"timezone": t["timezone"]}
                )
                tenants_by_name[t["name"]] = tenant

            for admin in ADMINS:
                if User.objects.filter(
                    email=admin["email"], tenant=tenants_by_name[admin["tenant"]]
                ).exists():
                    continue
                User.objects.create_user(
                    email=admin["email"],
                    password=DEMO_PASSWORD,
                    tenant=tenants_by_name[admin["tenant"]],
                    role=Role.ADMIN,
                )

        self.stdout.write(self.style.SUCCESS("Seed complete."))
```

**Step 11.4: Run — expect all seed tests pass**

**Step 11.5: Commit**

```bash
git commit -m "feat(seed): seed_demo creates 2 tenants and 2 admin accounts

--idempotent skips if data exists; --force wipes and reseeds.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 12: `apps/api/Dockerfile`

**Step 12.1: Write it**

```dockerfile
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY apps/api/pyproject.toml ./
RUN pip install --upgrade pip && pip install .[dev]

COPY apps/api/ .

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

**Step 12.2: Commit**

```bash
git commit -m "chore(ops): Dockerfile for api-django service

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 13: `docker-compose.yml` skeleton

**Step 13.1: Write it** (Phase 1 services only)

```yaml
services:
  db-postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports: ["5432:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 3s
      timeout: 3s
      retries: 20

  cache-redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  db-init:
    build:
      context: .
      dockerfile: apps/api/Dockerfile
    env_file: .env
    command: >
      sh -c "python manage.py migrate --no-input &&
             python manage.py seed_demo --idempotent"
    depends_on:
      db-postgres:
        condition: service_healthy

  api-django:
    build:
      context: .
      dockerfile: apps/api/Dockerfile
    env_file: .env
    ports: ["8000:8000"]
    depends_on:
      db-postgres:
        condition: service_healthy
      db-init:
        condition: service_completed_successfully

volumes:
  pgdata:
```

**Step 13.2: Manually smoke-test**

```bash
cp .env.example .env
docker compose up -d
sleep 20
curl -sf http://localhost:8000/api/v1/health
# expect {"ok": true, "tenant": null}

curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@westside.demo","password":"demo1234"}'
# expect access + refresh tokens
```

**Step 13.3: Commit**

```bash
git commit -m "chore(ops): docker-compose for db, redis, api-django, db-init

db-init runs migrate + seed_demo --idempotent before api-django starts.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 14: Automated compose smoke test

**Files:**
- Create: `ops/smoke-test.sh`

**Step 14.1: Script it**

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "→ Building and starting stack…"
docker compose up -d --build --wait

echo "→ Health check…"
for i in {1..30}; do
  if curl -sf http://localhost:8000/api/v1/health > /dev/null; then
    break
  fi
  sleep 1
done
curl -sf http://localhost:8000/api/v1/health | tee /dev/null | grep -q '"ok": true'

echo "→ Seeded admin login…"
RESPONSE=$(curl -sf -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@westside.demo","password":"demo1234"}')

echo "$RESPONSE" | grep -q '"access"'

echo "✓ Phase 1 smoke test passed"
```

**Step 14.2: Make executable and run**

```bash
chmod +x ops/smoke-test.sh
./ops/smoke-test.sh
```

**Step 14.3: Commit**

---

## Task 15: GitHub Actions CI

**Files:**
- Create: `.github/workflows/ci.yml`

**Step 15.1: Write it**

```yaml
name: CI
on: [push, pull_request]

jobs:
  api:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: hhps
          POSTGRES_PASSWORD: hhps_dev_only
          POSTGRES_DB: hhps_test
        ports: ["5432:5432"]
        options: >-
          --health-cmd="pg_isready -U hhps" --health-interval=3s
          --health-timeout=3s --health-retries=20
    env:
      POSTGRES_HOST: localhost
      POSTGRES_PORT: "5432"
      POSTGRES_USER: hhps
      POSTGRES_PASSWORD: hhps_dev_only
      POSTGRES_DB: hhps_test
      DJANGO_SECRET_KEY: test
      DJANGO_DEBUG: "1"
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.12"}
      - run: pip install -e "apps/api[dev]"
      - run: cd apps/api && ruff check .
      - run: cd apps/api && ruff format --check .
      - run: cd apps/api && pytest -v
```

**Step 15.2: Push to branch, watch CI turn green**

**Step 15.3: Commit**

---

## Task 16: Final Phase-1 README

**Step 16.1: Replace README with complete Phase-1 docs**

(Expand to include: full demo credentials table, what works, what doesn't, pointer to Phase 2 plan once it exists.)

**Step 16.2: Commit**

---

## Phase 1 Definition of Done

Phase 1 is complete when all of the following are true:

- [ ] `docker compose up -d` succeeds from a clean clone with only `cp .env.example .env` as prerequisite.
- [ ] `GET http://localhost:8000/api/v1/health` returns `{"ok": true, "tenant": null}` unauthenticated.
- [ ] `POST /api/v1/auth/login` with `admin@westside.demo` / `demo1234` returns access + refresh tokens.
- [ ] `GET /api/v1/health` with that access token returns `{"ok": true, "tenant": "Westside Home Health"}`.
- [ ] `make test` from repo root passes (expected: ~14 tests across core, tenancy, accounts, seed).
- [ ] `make lint` and `make type` are clean.
- [ ] `./ops/smoke-test.sh` completes with `✓ Phase 1 smoke test passed`.
- [ ] GitHub Actions CI is green on `main`.
- [ ] README documents how to run, credentials, and status.

---

## Handoff to Phase 2

Phase 2 plan will build on this foundation by adding: `Clinician`, `Patient`, `Visit`, `RoutePlan`, and `ClinicianPosition` models; CRUD endpoints for each; and their tenancy, permission, and serialization tests. No infrastructure changes.
