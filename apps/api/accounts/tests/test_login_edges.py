"""Edge cases around the /auth/login endpoint."""

import pytest
from rest_framework.test import APIClient

from accounts.models import Role, User
from tenancy.models import Tenant


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(name="Westside", timezone="UTC")


def test_login_missing_email_returns_400(tenant):
    client = APIClient()
    r = client.post("/api/v1/auth/login", {"password": "p"}, format="json")
    assert r.status_code == 400


def test_login_missing_password_returns_400(tenant):
    client = APIClient()
    r = client.post("/api/v1/auth/login", {"email": "x@y"}, format="json")
    assert r.status_code == 400


def test_login_wrong_password_returns_401(tenant):
    User.objects.create_user(email="u@x.demo", password="right", tenant=tenant, role=Role.ADMIN)
    client = APIClient()
    r = client.post(
        "/api/v1/auth/login",
        {"email": "u@x.demo", "password": "wrong"},
        format="json",
    )
    assert r.status_code == 401


def test_login_inactive_user_returns_401(tenant):
    user = User.objects.create_user(email="u@x.demo", password="p", tenant=tenant, role=Role.ADMIN)
    user.is_active = False
    user.save()
    client = APIClient()
    r = client.post(
        "/api/v1/auth/login",
        {"email": "u@x.demo", "password": "p"},
        format="json",
    )
    assert r.status_code == 401


def test_login_happy_path_returns_access_and_refresh(tenant):
    User.objects.create_user(email="ok@x.demo", password="p", tenant=tenant, role=Role.ADMIN)
    client = APIClient()
    r = client.post(
        "/api/v1/auth/login",
        {"email": "ok@x.demo", "password": "p"},
        format="json",
    )
    assert r.status_code == 200
    body = r.json()
    assert "access" in body and body["access"]
    assert "refresh" in body and body["refresh"]
    assert body["user"]["email"] == "ok@x.demo"
