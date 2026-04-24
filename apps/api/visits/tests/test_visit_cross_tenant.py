"""Cross-tenant isolation for the Visit REST API."""

from datetime import UTC, datetime, timedelta

import pytest
from rest_framework.test import APIClient

from accounts.models import Role, User
from clinicians.models import Credential
from patients.models import Patient
from tenancy.models import Tenant
from visits.models import Visit


@pytest.fixture
def two_tenants(db):
    ta = Tenant.objects.create(name="A", timezone="UTC")
    tb = Tenant.objects.create(name="B", timezone="UTC")
    pa = Patient.objects.create(
        tenant=ta,
        name="PA",
        phone="+1",
        address="x",
        lat=0,
        lon=0,
        required_skill=Credential.RN,
    )
    pb = Patient.objects.create(
        tenant=tb,
        name="PB",
        phone="+1",
        address="x",
        lat=0,
        lon=0,
        required_skill=Credential.RN,
    )
    start = datetime(2026, 4, 24, 10, 0, tzinfo=UTC)
    va = Visit.objects.create(
        tenant=ta,
        patient=pa,
        window_start=start,
        window_end=start + timedelta(hours=1),
        required_skill=Credential.RN,
    )
    vb = Visit.objects.create(
        tenant=tb,
        patient=pb,
        window_start=start,
        window_end=start + timedelta(hours=1),
        required_skill=Credential.RN,
    )
    return {"ta": ta, "tb": tb, "va": va, "vb": vb}


def _sched_client(tenant: Tenant, email: str) -> APIClient:
    User.objects.create_user(email=email, password="p", tenant=tenant, role=Role.SCHEDULER)
    client = APIClient()
    r = client.post("/api/v1/auth/login", {"email": email, "password": "p"}, format="json")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.json()['access']}")
    return client


def test_scheduler_lists_only_own_tenant_visits(two_tenants):
    client = _sched_client(two_tenants["ta"], "sa@a.demo")
    r = client.get("/api/v1/visits/")
    assert r.status_code == 200
    body = r.json()
    rows = body["results"] if isinstance(body, dict) else body
    ids = [v["id"] for v in rows]
    assert two_tenants["va"].id in ids
    assert two_tenants["vb"].id not in ids


def test_cross_tenant_retrieve_is_404(two_tenants):
    client = _sched_client(two_tenants["ta"], "sa@a.demo")
    r = client.get(f"/api/v1/visits/{two_tenants['vb'].id}/")
    assert r.status_code == 404


def test_cross_tenant_assign_is_404(two_tenants):
    client = _sched_client(two_tenants["ta"], "sa@a.demo")
    # Attempting to mutate tenant B's visit via tenant A's credentials.
    r = client.post(
        f"/api/v1/visits/{two_tenants['vb'].id}/assign/",
        {"clinician_id": 999},
        format="json",
    )
    assert r.status_code == 404
