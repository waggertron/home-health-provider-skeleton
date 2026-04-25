"""Phase 8 T4: Celery task wraps rollup_daily."""

from datetime import UTC, date, datetime, timedelta

import pytest
from django.test import override_settings

from accounts.models import Role, User
from clinicians.models import Clinician, Credential
from patients.models import Patient
from reporting.models import DailyAgencyStats
from reporting.tasks import rollup_daily_task
from tenancy.models import Tenant
from visits.models import Visit, VisitStatus


@pytest.fixture
def one_completed_visit(db):
    target = date(2026, 4, 23)
    day_start = datetime(2026, 4, 23, 9, 0, tzinfo=UTC)
    tenant = Tenant.objects.create(name="Westside", timezone="UTC")
    user = User.objects.create_user(
        email="rn@x.demo", password="p", tenant=tenant, role=Role.CLINICIAN
    )
    clinician = Clinician.objects.create(
        user=user, tenant=tenant, credential=Credential.RN, home_lat=0, home_lon=0
    )
    patient = Patient.objects.create(
        tenant=tenant, name="P", phone="+1", address="x", lat=0, lon=0,
        required_skill=Credential.RN,
    )
    Visit.objects.create(
        tenant=tenant,
        patient=patient,
        clinician=clinician,
        window_start=day_start,
        window_end=day_start + timedelta(hours=1),
        required_skill=Credential.RN,
        status=VisitStatus.COMPLETED,
        check_in_at=day_start + timedelta(minutes=2),
        check_out_at=day_start + timedelta(minutes=30),
    )
    return tenant, target


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
def test_rollup_daily_task_with_explicit_date_runs_rollup(one_completed_visit):
    tenant, target = one_completed_visit
    result = rollup_daily_task.delay(target_date=target.isoformat()).get(timeout=10)
    assert result["date"] == target.isoformat()
    assert result["clinician_rows"] == 1
    assert result["agency_rows"] == 1
    assert DailyAgencyStats.objects.filter(tenant=tenant, date=target).exists()


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
def test_rollup_daily_task_defaults_to_yesterday(one_completed_visit):
    """No date argument → task defaults to yesterday in the local tz.

    Yesterday's date will not match our seeded 2026-04-23 fixture, but the
    task should still complete (zero clinician_rows for tenants without
    activity).
    """
    result = rollup_daily_task.delay().get(timeout=10)
    assert "date" in result
    assert "clinician_rows" in result
