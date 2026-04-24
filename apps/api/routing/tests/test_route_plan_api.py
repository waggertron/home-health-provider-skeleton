"""RoutePlan REST API — read-only, tenant-scoped, scheduler/admin only."""

from datetime import date

import pytest
from rest_framework.test import APIClient

from accounts.models import Role, User
from clinicians.models import Clinician, Credential
from routing.models import RoutePlan
from tenancy.models import Tenant


@pytest.fixture
def two_tenants_with_plans(db):
    t1 = Tenant.objects.create(name="Westside", timezone="UTC")
    t2 = Tenant.objects.create(name="Sunset", timezone="UTC")
    u1 = User.objects.create_user(
        email="rn1@westside.demo", password="p", tenant=t1, role=Role.CLINICIAN
    )
    c1 = Clinician.objects.create(
        user=u1, tenant=t1, credential=Credential.RN, home_lat=0, home_lon=0
    )
    u2 = User.objects.create_user(
        email="rn2@sunset.demo", password="p", tenant=t2, role=Role.CLINICIAN
    )
    c2 = Clinician.objects.create(
        user=u2, tenant=t2, credential=Credential.RN, home_lat=0, home_lon=0
    )
    plan1 = RoutePlan.objects.create(
        tenant=t1, clinician=c1, date=date(2026, 4, 23), visits_ordered=[1, 2, 3]
    )
    plan2 = RoutePlan.objects.create(
        tenant=t2, clinician=c2, date=date(2026, 4, 23), visits_ordered=[10]
    )
    return {"t1": t1, "t2": t2, "plan1": plan1, "plan2": plan2}


def _auth_client(tenant: Tenant, role: str, email: str) -> APIClient:
    User.objects.create_user(email=email, password="p", tenant=tenant, role=role)
    client = APIClient()
    r = client.post("/api/v1/auth/login", {"email": email, "password": "p"}, format="json")
    assert r.status_code == 200
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.json()['access']}")
    return client


def test_unauthenticated_list_is_401(two_tenants_with_plans):
    r = APIClient().get("/api/v1/routeplans/")
    assert r.status_code == 401


def test_scheduler_lists_only_own_tenant_plans(two_tenants_with_plans):
    client = _auth_client(two_tenants_with_plans["t1"], Role.SCHEDULER, "s@westside.demo")
    r = client.get("/api/v1/routeplans/")
    assert r.status_code == 200
    assert [row["visits_ordered"] for row in r.json()] == [[1, 2, 3]]


def test_cross_tenant_retrieve_is_404(two_tenants_with_plans):
    plan2 = two_tenants_with_plans["plan2"]
    client = _auth_client(two_tenants_with_plans["t1"], Role.SCHEDULER, "s@westside.demo")
    r = client.get(f"/api/v1/routeplans/{plan2.id}/")
    assert r.status_code == 404


def test_clinician_role_cannot_list(two_tenants_with_plans):
    t1 = two_tenants_with_plans["t1"]
    client = _auth_client(t1, Role.CLINICIAN, "rn-extra@westside.demo")
    r = client.get("/api/v1/routeplans/")
    assert r.status_code == 403
