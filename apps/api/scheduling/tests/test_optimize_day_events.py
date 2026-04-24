"""Event wiring: optimize_day publishes schedule.optimized + visit.reassigned."""

from datetime import UTC, date, datetime, timedelta
from unittest.mock import patch

import pytest
from django.test import override_settings

from accounts.models import Role, User
from clinicians.models import Clinician, Credential
from patients.models import Patient
from scheduling.tasks import optimize_day
from tenancy.models import Tenant
from visits.models import Visit


@pytest.fixture
def optimize_events_fixture(db):
    tenant = Tenant.objects.create(name="Westside", timezone="UTC")
    u = User.objects.create_user(
        email="rn@x.demo", password="p", tenant=tenant, role=Role.CLINICIAN
    )
    Clinician.objects.create(
        user=u, tenant=tenant, credential=Credential.RN, home_lat=34.0, home_lon=-118.0
    )
    p = Patient.objects.create(
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
        patient=p,
        window_start=day_start,
        window_end=day_start + timedelta(hours=2),
        required_skill=Credential.RN,
    )
    return tenant, date(2026, 4, 24)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
def test_optimize_day_publishes_schedule_optimized_and_visit_reassigned(
    optimize_events_fixture,
):
    tenant, the_day = optimize_events_fixture
    with patch("scheduling.tasks.publish") as pub:
        optimize_day.delay(tenant.id, the_day.isoformat(), time_budget_s=1).get(timeout=15)

    event_types = [call.args[1]["type"] for call in pub.call_args_list]
    assert "schedule.optimized" in event_types
    assert "visit.reassigned" in event_types
    optimized = next(
        call.args[1] for call in pub.call_args_list if call.args[1]["type"] == "schedule.optimized"
    )
    assert optimized["tenant_id"] == tenant.id
    assert optimized["payload"]["date"] == the_day.isoformat()
    assert "routes" in optimized["payload"]
