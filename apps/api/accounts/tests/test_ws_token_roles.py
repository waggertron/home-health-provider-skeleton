"""ws-token endpoint works for every authenticated role."""

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import Role, User
from tenancy.models import Tenant


def _login(tenant: Tenant, email: str, role: str) -> APIClient:
    User.objects.create_user(email=email, password="p", tenant=tenant, role=role)
    client = APIClient()
    r = client.post("/api/v1/auth/login", {"email": email, "password": "p"}, format="json")
    assert r.status_code == 200, r.content
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.json()['access']}")
    return client


@pytest.mark.parametrize(
    "role",
    [Role.ADMIN, Role.SCHEDULER, Role.CLINICIAN],
)
def test_ws_token_works_for_every_role(db, role):
    tenant = Tenant.objects.create(name=f"Westside-{role}", timezone="UTC")
    client = _login(tenant, f"{role}@x.demo", role)
    r = client.post("/api/v1/auth/ws-token")
    assert r.status_code == 200, r.content
    decoded = AccessToken(r.json()["token"])
    assert decoded["scope"] == "ws"
    assert decoded["role"] == role
    assert decoded["tenant_id"] == tenant.id


def test_ws_token_tenants_are_isolated(db):
    """Two tenants' tokens carry distinct tenant_id claims."""
    t1 = Tenant.objects.create(name="A", timezone="UTC")
    t2 = Tenant.objects.create(name="B", timezone="UTC")
    c1 = _login(t1, "sched@a.demo", Role.SCHEDULER)
    c2 = _login(t2, "sched@b.demo", Role.SCHEDULER)

    tok1 = AccessToken(c1.post("/api/v1/auth/ws-token").json()["token"])
    tok2 = AccessToken(c2.post("/api/v1/auth/ws-token").json()["token"])
    assert tok1["tenant_id"] != tok2["tenant_id"]
    assert tok1["tenant_id"] == t1.id
    assert tok2["tenant_id"] == t2.id
