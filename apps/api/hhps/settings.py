"""
Django settings for the HHPS API.

Phase 1 scope: bootstrap Django with Postgres + DRF + SimpleJWT, no first-party
apps yet. Each subsequent task adds its own app to INSTALLED_APPS.
"""

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
]

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
