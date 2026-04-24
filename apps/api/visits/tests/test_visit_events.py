"""Event wiring: visit state transitions publish the right events."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from accounts.models import Role, User
from clinicians.models import Clinician, Credential
from patients.models import Patient
from tenancy.models import Tenant
from visits.models import Visit, VisitStatus
from visits.services import assign, cancel, check_in, check_out


@pytest.fixture
def visit_events_fixture(db):
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
    user = User.objects.create_user(
        email="rn@x.demo", password="p", tenant=tenant, role=Role.CLINICIAN
    )
    clinician = Clinician.objects.create(
        user=user, tenant=tenant, credential=Credential.RN, home_lat=0, home_lon=0
    )
    start = datetime(2026, 4, 23, 10, 0, tzinfo=UTC)
    visit = Visit.objects.create(
        tenant=tenant,
        patient=patient,
        window_start=start,
        window_end=start + timedelta(hours=1),
        required_skill=Credential.RN,
    )
    return tenant, patient, clinician, visit


def test_assign_publishes_visit_reassigned(visit_events_fixture):
    tenant, _, clinician, visit = visit_events_fixture
    with patch("visits.services.publish") as pub:
        assign(visit, clinician)
    assert pub.called
    channel_tenant, event = pub.call_args[0]
    assert channel_tenant == tenant.id
    assert event["type"] == "visit.reassigned"
    assert event["payload"]["visit_id"] == visit.id
    assert event["payload"]["clinician_id"] == clinician.id


def test_check_in_publishes_visit_status_changed(visit_events_fixture):
    _, _, clinician, visit = visit_events_fixture
    assign(visit, clinician)
    with patch("visits.services.publish") as pub:
        check_in(visit, lat=0, lon=0)
    assert pub.called
    _, event = pub.call_args[0]
    assert event["type"] == "visit.status_changed"
    assert event["payload"]["status"] == VisitStatus.ON_SITE


def test_check_out_publishes_visit_status_changed(visit_events_fixture):
    _, _, clinician, visit = visit_events_fixture
    assign(visit, clinician)
    check_in(visit, lat=0, lon=0)
    with patch("visits.services.publish") as pub:
        check_out(visit)
    assert pub.called
    _, event = pub.call_args[0]
    assert event["type"] == "visit.status_changed"
    assert event["payload"]["status"] == VisitStatus.COMPLETED


def test_cancel_publishes_visit_status_changed(visit_events_fixture):
    _, _, _, visit = visit_events_fixture
    with patch("visits.services.publish") as pub:
        cancel(visit, reason="patient unavailable")
    assert pub.called
    _, event = pub.call_args[0]
    assert event["type"] == "visit.status_changed"
    assert event["payload"]["status"] == VisitStatus.CANCELLED
