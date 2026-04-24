"""Event wiring: POST /positions/ publishes clinician.position_updated."""

from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from accounts.models import Role, User
from clinicians.models import Clinician, Credential
from tenancy.models import Tenant


@pytest.fixture
def position_events_fixture(db):
    tenant = Tenant.objects.create(name="Westside", timezone="UTC")
    user = User.objects.create_user(
        email="rn@x.demo", password="p", tenant=tenant, role=Role.CLINICIAN
    )
    Clinician.objects.create(
        user=user, tenant=tenant, credential=Credential.RN, home_lat=0, home_lon=0
    )
    client = APIClient()
    r = client.post(
        "/api/v1/auth/login",
        {"email": "rn@x.demo", "password": "p"},
        format="json",
    )
    assert r.status_code == 200
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.json()['access']}")
    return tenant, client


def test_position_create_publishes_clinician_position_updated(position_events_fixture):
    tenant, client = position_events_fixture
    with patch("clinicians.position_views.publish") as pub:
        r = client.post(
            "/api/v1/positions/",
            {"lat": 34.0, "lon": -118.0, "ts": "2026-04-24T10:00:00Z"},
            format="json",
        )
    assert r.status_code == 201, r.content
    assert pub.called
    channel_tenant, event = pub.call_args[0]
    assert channel_tenant == tenant.id
    assert event["type"] == "clinician.position_updated"
    assert event["payload"]["lat"] == 34.0
    assert event["payload"]["lon"] == -118.0
