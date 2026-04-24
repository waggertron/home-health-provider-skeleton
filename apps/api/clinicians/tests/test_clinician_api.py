"""Clinician REST API (list + retrieve). Tenant-scoped, scheduler/admin only."""

import pytest
from rest_framework.test import APIClient

from accounts.models import Role, User
from clinicians.models import Clinician, Credential
from tenancy.models import Tenant


@pytest.fixture
def two_tenants_with_clinicians(db):
    t1 = Tenant.objects.create(name="Westside", timezone="UTC")
    t2 = Tenant.objects.create(name="Sunset", timezone="UTC")

    # clinicians (with user accounts) in each tenant
    u1 = User.objects.create_user(
        email="rn1@westside.demo", password="p", tenant=t1, role=Role.CLINICIAN
    )
    c1 = Clinician.objects.create(
        user=u1, tenant=t1, credential=Credential.RN, home_lat=34.0, home_lon=-118.4
    )
    u2 = User.objects.create_user(
        email="rn2@sunset.demo", password="p", tenant=t2, role=Role.CLINICIAN
    )
    c2 = Clinician.objects.create(
        user=u2, tenant=t2, credential=Credential.LVN, home_lat=34.1, home_lon=-118.5
    )
    return {"t1": t1, "t2": t2, "c1": c1, "c2": c2}


def _auth_client(tenant: Tenant, role: str, email: str) -> APIClient:
    user = User.objects.create_user(email=email, password="p", tenant=tenant, role=role)
    client = APIClient()
    r = client.post("/api/v1/auth/login", {"email": email, "password": "p"}, format="json")
    assert r.status_code == 200, r.content
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.json()['access']}")
    return client


def test_unauthenticated_list_is_401(two_tenants_with_clinicians):
    r = APIClient().get("/api/v1/clinicians/")
    assert r.status_code == 401


def test_scheduler_lists_only_own_tenant_clinicians(two_tenants_with_clinicians):
    t1 = two_tenants_with_clinicians["t1"]
    client = _auth_client(t1, Role.SCHEDULER, "sched@westside.demo")
    r = client.get("/api/v1/clinicians/")
    assert r.status_code == 200
    body = r.json()
    emails = {row["email"] for row in body}
    assert emails == {"rn1@westside.demo"}


def test_scheduler_can_retrieve_own_tenant_clinician(two_tenants_with_clinicians):
    t1 = two_tenants_with_clinicians["t1"]
    c1 = two_tenants_with_clinicians["c1"]
    client = _auth_client(t1, Role.SCHEDULER, "sched@westside.demo")
    r = client.get(f"/api/v1/clinicians/{c1.id}/")
    assert r.status_code == 200
    assert r.json()["email"] == "rn1@westside.demo"


def test_cross_tenant_retrieve_is_404(two_tenants_with_clinicians):
    t1 = two_tenants_with_clinicians["t1"]
    c2 = two_tenants_with_clinicians["c2"]  # belongs to t2
    client = _auth_client(t1, Role.SCHEDULER, "sched@westside.demo")
    r = client.get(f"/api/v1/clinicians/{c2.id}/")
    assert r.status_code == 404


def test_clinician_role_cannot_list_other_clinicians(two_tenants_with_clinicians):
    t1 = two_tenants_with_clinicians["t1"]
    client = _auth_client(t1, Role.CLINICIAN, "other-rn@westside.demo")
    r = client.get("/api/v1/clinicians/")
    assert r.status_code == 403
