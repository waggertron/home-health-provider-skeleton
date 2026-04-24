"""Visit REST API + state-machine actions."""

from datetime import UTC, datetime, timedelta

import pytest
from rest_framework.test import APIClient

from accounts.models import Role, User
from clinicians.models import Clinician, Credential
from patients.models import Patient
from tenancy.models import Tenant
from visits.models import Visit, VisitStatus


@pytest.fixture
def demo_tenant(db):
    tenant = Tenant.objects.create(name="Westside", timezone="UTC")
    patient = Patient.objects.create(
        tenant=tenant,
        name="Jane",
        phone="+1",
        address="x",
        lat=0,
        lon=0,
        required_skill=Credential.RN,
    )
    rn_user = User.objects.create_user(
        email="rn@westside.demo", password="p", tenant=tenant, role=Role.CLINICIAN
    )
    clinician = Clinician.objects.create(
        user=rn_user,
        tenant=tenant,
        credential=Credential.RN,
        home_lat=0,
        home_lon=0,
    )
    start = datetime(2026, 4, 23, 10, 0, tzinfo=UTC)
    visit = Visit.objects.create(
        tenant=tenant,
        patient=patient,
        window_start=start,
        window_end=start + timedelta(hours=1),
        required_skill=Credential.RN,
    )
    return {"tenant": tenant, "patient": patient, "clinician": clinician, "visit": visit}


def _scheduler_client(tenant: Tenant) -> APIClient:
    User.objects.create_user(
        email="sched@westside.demo", password="p", tenant=tenant, role=Role.SCHEDULER
    )
    client = APIClient()
    r = client.post(
        "/api/v1/auth/login",
        {"email": "sched@westside.demo", "password": "p"},
        format="json",
    )
    assert r.status_code == 200
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.json()['access']}")
    return client


def test_unauthenticated_list_is_401(demo_tenant):
    r = APIClient().get("/api/v1/visits/")
    assert r.status_code == 401


def test_scheduler_lists_visits_in_own_tenant(demo_tenant):
    client = _scheduler_client(demo_tenant["tenant"])
    r = client.get("/api/v1/visits/")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_assign_visit_happy_path(demo_tenant):
    client = _scheduler_client(demo_tenant["tenant"])
    visit_id = demo_tenant["visit"].id
    clinician_id = demo_tenant["clinician"].id
    r = client.post(
        f"/api/v1/visits/{visit_id}/assign/",
        {"clinician_id": clinician_id},
        format="json",
    )
    assert r.status_code == 200, r.content
    assert r.json()["status"] == VisitStatus.ASSIGNED
    assert r.json()["clinician"] == clinician_id


def test_assign_visit_already_assigned_is_409(demo_tenant):
    client = _scheduler_client(demo_tenant["tenant"])
    visit_id = demo_tenant["visit"].id
    clinician_id = demo_tenant["clinician"].id
    client.post(
        f"/api/v1/visits/{visit_id}/assign/",
        {"clinician_id": clinician_id},
        format="json",
    )
    r = client.post(
        f"/api/v1/visits/{visit_id}/assign/",
        {"clinician_id": clinician_id},
        format="json",
    )
    assert r.status_code == 409


def test_check_in_after_assign_promotes_to_on_site(demo_tenant):
    client = _scheduler_client(demo_tenant["tenant"])
    visit_id = demo_tenant["visit"].id
    client.post(
        f"/api/v1/visits/{visit_id}/assign/",
        {"clinician_id": demo_tenant["clinician"].id},
        format="json",
    )
    r = client.post(
        f"/api/v1/visits/{visit_id}/check-in/",
        {"lat": 34.0, "lon": -118.0},
        format="json",
    )
    assert r.status_code == 200
    assert r.json()["status"] == VisitStatus.ON_SITE
    assert r.json()["check_in_at"] is not None


def test_check_out_from_on_site_promotes_to_completed(demo_tenant):
    client = _scheduler_client(demo_tenant["tenant"])
    visit_id = demo_tenant["visit"].id
    client.post(
        f"/api/v1/visits/{visit_id}/assign/",
        {"clinician_id": demo_tenant["clinician"].id},
        format="json",
    )
    client.post(
        f"/api/v1/visits/{visit_id}/check-in/",
        {"lat": 0, "lon": 0},
        format="json",
    )
    r = client.post(
        f"/api/v1/visits/{visit_id}/check-out/",
        {"notes": "Dressing changed."},
        format="json",
    )
    assert r.status_code == 200
    assert r.json()["status"] == VisitStatus.COMPLETED
    assert "Dressing" in r.json()["notes"]


def test_cancel_scheduled_visit_succeeds(demo_tenant):
    client = _scheduler_client(demo_tenant["tenant"])
    visit_id = demo_tenant["visit"].id
    r = client.post(
        f"/api/v1/visits/{visit_id}/cancel/",
        {"reason": "patient no-show"},
        format="json",
    )
    assert r.status_code == 200
    assert r.json()["status"] == VisitStatus.CANCELLED


def test_cancel_completed_visit_is_409(demo_tenant):
    client = _scheduler_client(demo_tenant["tenant"])
    visit_id = demo_tenant["visit"].id
    client.post(
        f"/api/v1/visits/{visit_id}/assign/",
        {"clinician_id": demo_tenant["clinician"].id},
        format="json",
    )
    client.post(
        f"/api/v1/visits/{visit_id}/check-in/",
        {"lat": 0, "lon": 0},
        format="json",
    )
    client.post(
        f"/api/v1/visits/{visit_id}/check-out/",
        {"notes": ""},
        format="json",
    )
    r = client.post(
        f"/api/v1/visits/{visit_id}/cancel/",
        {"reason": "too late"},
        format="json",
    )
    assert r.status_code == 409
