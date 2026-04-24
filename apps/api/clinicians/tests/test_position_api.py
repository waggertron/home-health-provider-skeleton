"""ClinicianPosition REST API — create by clinician, latest by scheduler."""

from datetime import UTC, datetime, timedelta

import pytest
from rest_framework.test import APIClient

from accounts.models import Role, User
from clinicians.models import Clinician, ClinicianPosition, Credential
from tenancy.models import Tenant


@pytest.fixture
def tenant_with_clinicians(db):
    tenant = Tenant.objects.create(name="Westside", timezone="UTC")
    users = [
        User.objects.create_user(
            email=f"rn{i}@westside.demo", password="p", tenant=tenant, role=Role.CLINICIAN
        )
        for i in range(2)
    ]
    clinicians = [
        Clinician.objects.create(
            user=u, tenant=tenant, credential=Credential.RN, home_lat=0, home_lon=0
        )
        for u in users
    ]
    return {"tenant": tenant, "users": users, "clinicians": clinicians}


def _login(email: str, password: str = "p") -> APIClient:
    client = APIClient()
    r = client.post("/api/v1/auth/login", {"email": email, "password": password}, format="json")
    assert r.status_code == 200
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.json()['access']}")
    return client


def test_clinician_posts_own_position(tenant_with_clinicians):
    users = tenant_with_clinicians["users"]
    client = _login(users[0].email)
    r = client.post(
        "/api/v1/positions/",
        {"lat": 34.0, "lon": -118.0, "ts": "2026-04-23T10:00:00Z"},
        format="json",
    )
    assert r.status_code == 201, r.content
    assert ClinicianPosition.objects.count() == 1
    saved = ClinicianPosition.objects.first()
    assert saved.clinician_id == tenant_with_clinicians["clinicians"][0].id


def test_scheduler_cannot_post_position(tenant_with_clinicians):
    tenant = tenant_with_clinicians["tenant"]
    User.objects.create_user(
        email="sched@westside.demo", password="p", tenant=tenant, role=Role.SCHEDULER
    )
    client = _login("sched@westside.demo")
    r = client.post(
        "/api/v1/positions/",
        {"lat": 0, "lon": 0, "ts": "2026-04-23T10:00:00Z"},
        format="json",
    )
    assert r.status_code == 403


def test_latest_returns_one_row_per_clinician(tenant_with_clinicians):
    tenant = tenant_with_clinicians["tenant"]
    clinicians = tenant_with_clinicians["clinicians"]
    base = datetime(2026, 4, 23, 10, 0, tzinfo=UTC)
    for i, c in enumerate(clinicians):
        for offset in range(3):
            ClinicianPosition.objects.create(
                tenant=tenant,
                clinician=c,
                lat=34.0 + i * 0.1 + offset * 0.01,
                lon=-118.0,
                ts=base + timedelta(minutes=offset + i * 10),
            )

    User.objects.create_user(
        email="sched@westside.demo", password="p", tenant=tenant, role=Role.SCHEDULER
    )
    client = _login("sched@westside.demo")
    r = client.get("/api/v1/positions/latest/")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 2
    latest_by_clinician = {row["clinician"]: row for row in body}
    # Each clinician's returned row should be the latest of the three we inserted.
    assert latest_by_clinician[clinicians[0].id]["lat"] == pytest.approx(34.02)
    assert latest_by_clinician[clinicians[1].id]["lat"] == pytest.approx(34.12)


def test_latest_unauthenticated_is_401(tenant_with_clinicians):
    r = APIClient().get("/api/v1/positions/latest/")
    assert r.status_code == 401


def test_cross_tenant_latest_is_empty_for_other_tenant(tenant_with_clinicians):
    tenant = tenant_with_clinicians["tenant"]
    clinicians = tenant_with_clinicians["clinicians"]
    ClinicianPosition.objects.create(
        tenant=tenant,
        clinician=clinicians[0],
        lat=34.0,
        lon=-118.0,
        ts=datetime(2026, 4, 23, 10, 0, tzinfo=UTC),
    )

    other_tenant = Tenant.objects.create(name="Other", timezone="UTC")
    User.objects.create_user(
        email="sched@other.demo", password="p", tenant=other_tenant, role=Role.SCHEDULER
    )
    client = _login("sched@other.demo")
    r = client.get("/api/v1/positions/latest/")
    assert r.status_code == 200
    assert r.json() == []
