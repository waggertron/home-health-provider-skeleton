"""SMS read-only API — scheduler/admin only, tenant-scoped."""

import pytest
from rest_framework.test import APIClient

from accounts.models import Role, User
from messaging.models import SmsOutbox
from tenancy.models import Tenant


@pytest.fixture
def two_tenants_with_sms(db):
    t1 = Tenant.objects.create(name="Westside", timezone="UTC")
    t2 = Tenant.objects.create(name="Sunset", timezone="UTC")
    SmsOutbox.objects.create(tenant=t1, template="visit_reminder", body="See you soon.")
    SmsOutbox.objects.create(tenant=t2, template="visit_reminder", body="Other tenant.")
    return {"t1": t1, "t2": t2}


def _auth_client(tenant: Tenant, role: str, email: str) -> APIClient:
    User.objects.create_user(email=email, password="p", tenant=tenant, role=role)
    client = APIClient()
    r = client.post("/api/v1/auth/login", {"email": email, "password": "p"}, format="json")
    assert r.status_code == 200
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.json()['access']}")
    return client


def test_unauthenticated_list_is_401(two_tenants_with_sms):
    r = APIClient().get("/api/v1/sms/")
    assert r.status_code == 401


def test_scheduler_lists_only_own_tenant_sms(two_tenants_with_sms):
    t1 = two_tenants_with_sms["t1"]
    client = _auth_client(t1, Role.SCHEDULER, "s@westside.demo")
    r = client.get("/api/v1/sms/")
    assert r.status_code == 200
    bodies = {row["body"] for row in r.json()}
    assert bodies == {"See you soon."}


def test_clinician_role_cannot_list(two_tenants_with_sms):
    t1 = two_tenants_with_sms["t1"]
    client = _auth_client(t1, Role.CLINICIAN, "rn-extra@westside.demo")
    r = client.get("/api/v1/sms/")
    assert r.status_code == 403
