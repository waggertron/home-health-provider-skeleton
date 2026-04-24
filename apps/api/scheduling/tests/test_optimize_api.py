"""REST endpoint for enqueuing a VRP optimize for a (tenant, date)."""

from datetime import UTC, date, datetime, timedelta

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from accounts.models import Role, User
from clinicians.models import Clinician, Credential
from patients.models import Patient
from tenancy.models import Tenant
from visits.models import Visit


@pytest.fixture
def schedule_api_fixture(db):
    tenant = Tenant.objects.create(name="Westside", timezone="UTC")
    u_rn = User.objects.create_user(
        email="rn@westside.demo", password="p", tenant=tenant, role=Role.CLINICIAN
    )
    Clinician.objects.create(
        user=u_rn, tenant=tenant, credential=Credential.RN, home_lat=34.0, home_lon=-118.0
    )
    patient = Patient.objects.create(
        tenant=tenant,
        name="P",
        phone="+1",
        address="x",
        lat=34.01,
        lon=-118.0,
        required_skill=Credential.RN,
    )
    day_start = datetime(2026, 4, 24, 9, 0, tzinfo=UTC)
    Visit.objects.create(
        tenant=tenant,
        patient=patient,
        window_start=day_start,
        window_end=day_start + timedelta(hours=2),
        required_skill=Credential.RN,
    )
    return tenant, date(2026, 4, 24)


def _token_client(tenant: Tenant, email: str, role: str) -> APIClient:
    User.objects.create_user(email=email, password="p", tenant=tenant, role=role)
    client = APIClient()
    r = client.post("/api/v1/auth/login", {"email": email, "password": "p"}, format="json")
    assert r.status_code == 200, r.content
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.json()['access']}")
    return client


def test_optimize_endpoint_requires_authentication(schedule_api_fixture):
    _, the_day = schedule_api_fixture
    client = APIClient()
    r = client.post(f"/api/v1/schedule/{the_day.isoformat()}/optimize")
    assert r.status_code == 401


def test_optimize_endpoint_forbids_clinician_role(schedule_api_fixture):
    tenant, the_day = schedule_api_fixture
    client = _token_client(tenant, "cli@westside.demo", Role.CLINICIAN)
    r = client.post(f"/api/v1/schedule/{the_day.isoformat()}/optimize")
    assert r.status_code == 403


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
def test_optimize_endpoint_happy_path_returns_202_with_job_id(schedule_api_fixture):
    tenant, the_day = schedule_api_fixture
    client = _token_client(tenant, "sched@westside.demo", Role.SCHEDULER)
    r = client.post(f"/api/v1/schedule/{the_day.isoformat()}/optimize")
    assert r.status_code == 202, r.content
    body = r.json()
    assert "job_id" in body and body["job_id"]
    assert body["status"] in {"PENDING", "SUCCESS", "STARTED"}


def test_optimize_endpoint_rejects_malformed_date(schedule_api_fixture):
    tenant, _ = schedule_api_fixture
    client = _token_client(tenant, "sched@westside.demo", Role.SCHEDULER)
    r = client.post("/api/v1/schedule/not-a-date/optimize")
    assert r.status_code == 400
