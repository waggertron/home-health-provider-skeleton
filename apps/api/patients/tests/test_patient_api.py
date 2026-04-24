"""Patient REST API — full CRUD, tenant-scoped, scheduler/admin only."""

import pytest
from rest_framework.test import APIClient

from accounts.models import Role, User
from clinicians.models import Credential
from patients.models import Patient
from tenancy.models import Tenant


@pytest.fixture
def two_tenants_with_patients(db):
    t1 = Tenant.objects.create(name="Westside", timezone="UTC")
    t2 = Tenant.objects.create(name="Sunset", timezone="UTC")
    p1 = Patient.objects.create(
        tenant=t1,
        name="Alice",
        phone="+13105551111",
        address="1 A St",
        lat=34.0,
        lon=-118.0,
        required_skill=Credential.RN,
    )
    p2 = Patient.objects.create(
        tenant=t2,
        name="Bob",
        phone="+13105552222",
        address="2 B St",
        lat=34.1,
        lon=-118.1,
        required_skill=Credential.LVN,
    )
    return {"t1": t1, "t2": t2, "p1": p1, "p2": p2}


def _auth_client(tenant: Tenant, role: str, email: str) -> APIClient:
    User.objects.create_user(email=email, password="p", tenant=tenant, role=role)
    client = APIClient()
    r = client.post("/api/v1/auth/login", {"email": email, "password": "p"}, format="json")
    assert r.status_code == 200
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.json()['access']}")
    return client


def test_unauthenticated_list_is_401(two_tenants_with_patients):
    r = APIClient().get("/api/v1/patients/")
    assert r.status_code == 401


def test_scheduler_lists_only_own_tenant_patients(two_tenants_with_patients):
    t1 = two_tenants_with_patients["t1"]
    client = _auth_client(t1, Role.SCHEDULER, "s@westside.demo")
    r = client.get("/api/v1/patients/")
    assert r.status_code == 200
    names = {row["name"] for row in r.json()}
    assert names == {"Alice"}


def test_scheduler_creates_patient_and_tenant_is_stamped(two_tenants_with_patients):
    t1 = two_tenants_with_patients["t1"]
    client = _auth_client(t1, Role.SCHEDULER, "s@westside.demo")
    r = client.post(
        "/api/v1/patients/",
        {
            "name": "Charlie",
            "phone": "+13105553333",
            "address": "3 C St",
            "lat": 34.2,
            "lon": -118.2,
            "required_skill": Credential.MA,
            "preferences": {},
        },
        format="json",
    )
    assert r.status_code == 201, r.content
    created = Patient.objects.get(name="Charlie")
    assert created.tenant_id == t1.id


def test_scheduler_updates_patient(two_tenants_with_patients):
    t1 = two_tenants_with_patients["t1"]
    p1 = two_tenants_with_patients["p1"]
    client = _auth_client(t1, Role.SCHEDULER, "s@westside.demo")
    r = client.patch(
        f"/api/v1/patients/{p1.id}/",
        {"phone": "+13109999999"},
        format="json",
    )
    assert r.status_code == 200
    p1.refresh_from_db()
    assert p1.phone == "+13109999999"


def test_cross_tenant_retrieve_is_404(two_tenants_with_patients):
    t1 = two_tenants_with_patients["t1"]
    p2 = two_tenants_with_patients["p2"]
    client = _auth_client(t1, Role.SCHEDULER, "s@westside.demo")
    r = client.get(f"/api/v1/patients/{p2.id}/")
    assert r.status_code == 404


def test_clinician_role_cannot_list(two_tenants_with_patients):
    t1 = two_tenants_with_patients["t1"]
    client = _auth_client(t1, Role.CLINICIAN, "rn-extra@westside.demo")
    r = client.get("/api/v1/patients/")
    assert r.status_code == 403
