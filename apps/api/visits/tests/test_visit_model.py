from datetime import UTC, datetime, timedelta

import pytest
from django.db import IntegrityError

from accounts.models import Role, User
from clinicians.models import Clinician, Credential
from patients.models import Patient
from tenancy.managers import clear_current_tenant, set_current_tenant
from tenancy.models import Tenant
from visits.models import Visit, VisitStatus


@pytest.fixture
def visit_fixtures(db):
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
        user=user,
        tenant=tenant,
        credential=Credential.RN,
        home_lat=0,
        home_lon=0,
    )
    return tenant, patient, clinician


def _window(hours: int = 1) -> tuple[datetime, datetime]:
    start = datetime(2026, 4, 23, 10, 0, tzinfo=UTC)
    return start, start + timedelta(hours=hours)


def test_visit_defaults_status_scheduled_and_clinician_is_nullable(visit_fixtures):
    tenant, patient, _ = visit_fixtures
    start, end = _window()
    v = Visit.objects.create(
        tenant=tenant,
        patient=patient,
        window_start=start,
        window_end=end,
        required_skill=Credential.RN,
    )
    assert v.status == VisitStatus.SCHEDULED
    assert v.clinician is None
    assert v.check_in_at is None
    assert v.check_out_at is None
    assert v.notes == ""
    assert v.ordering_seq is None


def test_visit_str_includes_patient_and_status(visit_fixtures):
    tenant, patient, _ = visit_fixtures
    start, end = _window()
    v = Visit.objects.create(
        tenant=tenant,
        patient=patient,
        window_start=start,
        window_end=end,
        required_skill=Credential.RN,
    )
    assert "Jane" in str(v)
    assert "scheduled" in str(v).lower()


def test_visit_status_enum_accepts_all_known_states(visit_fixtures):
    tenant, patient, _ = visit_fixtures
    start, end = _window()
    for state in (
        VisitStatus.SCHEDULED,
        VisitStatus.ASSIGNED,
        VisitStatus.EN_ROUTE,
        VisitStatus.ON_SITE,
        VisitStatus.COMPLETED,
        VisitStatus.CANCELLED,
        VisitStatus.MISSED,
    ):
        Visit.objects.create(
            tenant=tenant,
            patient=patient,
            window_start=start,
            window_end=end,
            required_skill=Credential.RN,
            status=state,
        )
    assert Visit.objects.count() == 7


def test_visit_rejects_inverted_window(visit_fixtures):
    tenant, patient, _ = visit_fixtures
    start, end = _window()
    with pytest.raises(IntegrityError):
        Visit.objects.create(
            tenant=tenant,
            patient=patient,
            window_start=end,
            window_end=start,
            required_skill=Credential.RN,
        )


def test_scoped_manager_filters_visits_by_current_tenant(visit_fixtures):
    tenant, patient, _ = visit_fixtures
    other_tenant = Tenant.objects.create(name="Other", timezone="UTC")
    other_patient = Patient.objects.create(
        tenant=other_tenant,
        name="P2",
        phone="+1",
        address="x",
        lat=0,
        lon=0,
        required_skill=Credential.RN,
    )
    start, end = _window()
    for t, p in [(tenant, patient), (other_tenant, other_patient)]:
        Visit.objects.create(
            tenant=t,
            patient=p,
            window_start=start,
            window_end=end,
            required_skill=Credential.RN,
        )

    set_current_tenant(tenant)
    try:
        assert Visit.scoped.count() == 1
    finally:
        clear_current_tenant()
