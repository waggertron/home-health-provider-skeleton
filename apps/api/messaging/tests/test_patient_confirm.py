"""Patient SMS confirmation public endpoint (post-v1 #2).

Tokens are HMAC-signed with TTL (Django TimestampSigner under the
project's SECRET_KEY). Replay protection comes from the visit row
itself — once `patient_confirmed_at` is stamped, the token is dead.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from django.test import Client
from django.utils import timezone

from clinicians.models import Clinician
from messaging.patient_confirm import sign_visit_token
from patients.models import Patient
from tenancy.managers import set_current_tenant
from tenancy.models import Tenant
from visits.models import Visit, VisitStatus


@pytest.fixture
def visit(db):
    tenant = Tenant.objects.create(
        name="Westside Demo",
        timezone="America/Los_Angeles",
        home_base_lat=34.0,
        home_base_lon=-118.0,
    )
    set_current_tenant(tenant)
    from accounts.models import Role, User

    user = User.objects.create(
        email="rn@westside.demo", tenant=tenant, role=Role.CLINICIAN, is_active=True
    )
    clinician = Clinician.objects.create(
        user=user, tenant=tenant, credential="RN", home_lat=34.0, home_lon=-118.0
    )
    patient = Patient.objects.create(
        tenant=tenant,
        name="Ada Lovelace",
        phone="+15551234567",
        address="1 Main St",
        lat=34.05,
        lon=-118.25,
        required_skill="RN",
    )
    return Visit.objects.create(
        tenant=tenant,
        patient=patient,
        clinician=clinician,
        window_start=timezone.now() + timedelta(hours=1),
        window_end=timezone.now() + timedelta(hours=2),
        required_skill="RN",
        status=VisitStatus.ASSIGNED,
    )


@pytest.mark.django_db
def test_get_with_valid_token_renders_visit_summary(visit):
    token = sign_visit_token(visit.id)
    response = Client().get(f"/p/{token}")
    assert response.status_code == 200
    body = response.content.decode()
    assert "Ada Lovelace" in body
    assert "Confirm" in body


@pytest.mark.django_db
def test_post_confirm_stamps_visit_and_publishes_event(visit):
    token = sign_visit_token(visit.id)
    with patch("messaging.public_views.publish") as pub:
        response = Client().post(f"/p/{token}/confirm")
    assert response.status_code == 200
    visit.refresh_from_db()
    assert visit.patient_confirmed_at is not None
    pub.assert_called_once()
    args, _ = pub.call_args
    assert args[0] == visit.tenant_id
    event = args[1]
    assert event["type"] == "visit.patient_confirmed"
    assert event["payload"]["visit_id"] == visit.id


@pytest.mark.django_db
def test_post_confirm_is_idempotent_returns_410_on_replay(visit):
    visit.patient_confirmed_at = datetime.now(UTC)
    visit.save(update_fields=["patient_confirmed_at"])
    token = sign_visit_token(visit.id)
    response = Client().post(f"/p/{token}/confirm")
    assert response.status_code == 410


@pytest.mark.django_db
def test_get_with_expired_token_returns_410(visit):
    token = sign_visit_token(visit.id)
    # Force unsign max_age to 0 by patching the verify path.
    with patch("messaging.patient_confirm.MAX_AGE_SECONDS", 0):
        response = Client().get(f"/p/{token}")
    assert response.status_code == 410


@pytest.mark.django_db
def test_get_with_malformed_token_returns_400(visit):
    response = Client().get("/p/not-a-real-token")
    assert response.status_code == 400


@pytest.mark.django_db
def test_get_with_tampered_token_returns_400(visit):
    token = sign_visit_token(visit.id)
    tampered = token[:-3] + "xxx"
    response = Client().get(f"/p/{tampered}")
    assert response.status_code == 400
