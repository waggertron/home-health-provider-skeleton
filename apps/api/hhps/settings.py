"""
Django settings for the HHPS API.

Phase 1 scope: bootstrap Django with Postgres + DRF + SimpleJWT, no first-party
apps yet. Each subsequent task adds its own app to INSTALLED_APPS.
"""

import hashlib
import os
from datetime import timedelta
from pathlib import Path

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
    "core",
    "tenancy",
    "accounts",
    "seed",
    "clinicians",
    "patients",
    "visits",
    "routing",
    "messaging",
    "scheduling",
    "reporting",
]

# Celery
_REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
_REDIS_PORT = os.environ.get("REDIS_PORT", "6379")
_REDIS_URL = f"redis://{_REDIS_HOST}:{_REDIS_PORT}"
CELERY_BROKER_URL = f"{_REDIS_URL}/0"
CELERY_RESULT_BACKEND = f"{_REDIS_URL}/0"
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "America/Los_Angeles"
# Tests flip this to True via @override_settings to run tasks inline.
CELERY_TASK_ALWAYS_EAGER = False

# Phase 4 events: publish domain events on tenant-scoped channels for rt-node fanout.
# Same Redis instance as the broker; PUBLISH is distinct from queue semantics.
EVENTS_REDIS_URL = f"{_REDIS_URL}/0"

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]

# auth.E003: USERNAME_FIELD uniqueness. Our User model has per-tenant email
# uniqueness (tenant_id, email) — not globally unique. Django's default
# ModelBackend will raise MultipleObjectsReturned if the same email ever
# exists in two tenants. Phase 1 demo seed uses distinct emails so this is
# safe. Phase 2+ may replace the auth backend with a tenant-aware one.
SILENCED_SYSTEM_CHECKS = ["auth.E003"]

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

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
}

# Ensure the HMAC signing key is always at least 32 bytes so PyJWT doesn't
# emit InsecureKeyLengthWarning under short dev/test SECRET_KEY values. In
# production, SECRET_KEY must be generated long in the first place; this
# guard exists so short test keys don't corrupt local/CI output.
_SIGNING_KEY = (
    SECRET_KEY
    if len(SECRET_KEY.encode("utf-8")) >= 32
    else hashlib.sha256(SECRET_KEY.encode("utf-8")).hexdigest()
)

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "SIGNING_KEY": _SIGNING_KEY,
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Los_Angeles"
USE_I18N = False
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
STATIC_URL = "static/"
