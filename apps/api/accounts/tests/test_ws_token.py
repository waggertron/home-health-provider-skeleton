"""Short-lived WS auth token endpoint (Phase 4 T3)."""

import time

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import Role, User
from tenancy.models import Tenant


@pytest.fixture
def ws_token_fixture(db):
    tenant = Tenant.objects.create(name="Westside", timezone="UTC")
    User.objects.create_user(email="sched@x.demo", password="p", tenant=tenant, role=Role.SCHEDULER)
    client = APIClient()
    r = client.post("/api/v1/auth/login", {"email": "sched@x.demo", "password": "p"}, format="json")
    assert r.status_code == 200
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.json()['access']}")
    return tenant, client


def test_ws_token_requires_authentication():
    client = APIClient()
    r = client.post("/api/v1/auth/ws-token")
    assert r.status_code == 401


def test_ws_token_returns_token_and_expiry(ws_token_fixture):
    _, client = ws_token_fixture
    r = client.post("/api/v1/auth/ws-token")
    assert r.status_code == 200, r.content
    body = r.json()
    assert "token" in body and body["token"]
    assert body["expires_in"] == 60


def test_ws_token_has_scope_tenant_and_role_claims(ws_token_fixture):
    tenant, client = ws_token_fixture
    r = client.post("/api/v1/auth/ws-token")
    assert r.status_code == 200
    decoded = AccessToken(r.json()["token"])
    assert decoded["scope"] == "ws"
    assert decoded["tenant_id"] == tenant.id
    assert decoded["role"] == Role.SCHEDULER


def test_ws_token_expiry_is_60s_window(ws_token_fixture):
    _, client = ws_token_fixture
    issued_at = int(time.time())
    r = client.post("/api/v1/auth/ws-token")
    decoded = AccessToken(r.json()["token"])
    exp = decoded["exp"]
    assert 55 <= exp - issued_at <= 65
