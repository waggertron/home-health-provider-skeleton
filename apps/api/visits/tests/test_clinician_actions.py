"""Phase 9: clinicians can list + check-in/check-out their own visits."""

from datetime import UTC, datetime, timedelta

import pytest
from rest_framework.test import APIClient

from accounts.models import Role, User
from clinicians.models import Clinician, Credential
from patients.models import Patient
from tenancy.models import Tenant
from visits.models import Visit, VisitStatus


@pytest.fixture
def assigned_visit_for_clinician(db):
    tenant = Tenant.objects.create(name="Westside", timezone="UTC")
    user = User.objects.create_user(
        email="rn@x.demo", password="p", tenant=tenant, role=Role.CLINICIAN
    )
    clinician = Clinician.objects.create(
        user=user, tenant=tenant, credential=Credential.RN, home_lat=0, home_lon=0
    )
    patient = Patient.objects.create(
        tenant=tenant,
        name="P",
        phone="+1",
        address="x",
        lat=0,
        lon=0,
        required_skill=Credential.RN,
    )
    start = datetime(2026, 4, 24, 10, 0, tzinfo=UTC)
    visit = Visit.objects.create(
        tenant=tenant,
        patient=patient,
        clinician=clinician,
        window_start=start,
        window_end=start + timedelta(hours=1),
        required_skill=Credential.RN,
        status=VisitStatus.ASSIGNED,
    )
    client = APIClient()
    r = client.post(
        "/api/v1/auth/login",
        {"email": "rn@x.demo", "password": "p"},
        format="json",
    )
    assert r.status_code == 200, r.content
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.json()['access']}")
    return tenant, clinician, visit, client


def test_clinician_can_list_visits(assigned_visit_for_clinician):
    _, _, _, client = assigned_visit_for_clinician
    r = client.get("/api/v1/visits/")
    assert r.status_code == 200, r.content


def test_clinician_can_check_in_assigned_visit(assigned_visit_for_clinician):
    _, _, visit, client = assigned_visit_for_clinician
    r = client.post(
        f"/api/v1/visits/{visit.id}/check-in/",
        {"lat": 34.05, "lon": -118.25},
        format="json",
    )
    assert r.status_code == 200, r.content
    assert r.json()["status"] == VisitStatus.ON_SITE


def test_clinician_cannot_assign_visits(assigned_visit_for_clinician):
    """Assignment is still scheduler/admin only — verify the role split holds."""
    _, _, visit, client = assigned_visit_for_clinician
    r = client.post(
        f"/api/v1/visits/{visit.id}/assign/",
        {"clinician_id": 999},
        format="json",
    )
    assert r.status_code == 403


def test_clinician_can_check_out_after_check_in(assigned_visit_for_clinician):
    _, _, visit, client = assigned_visit_for_clinician
    client.post(f"/api/v1/visits/{visit.id}/check-in/", {"lat": 0, "lon": 0}, format="json")
    r = client.post(
        f"/api/v1/visits/{visit.id}/check-out/",
        {"notes": "all good"},
        format="json",
    )
    assert r.status_code == 200, r.content
    assert r.json()["status"] == VisitStatus.COMPLETED
