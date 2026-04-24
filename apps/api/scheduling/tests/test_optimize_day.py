from datetime import UTC, date, datetime, timedelta

import pytest
from django.test import override_settings

from accounts.models import Role, User
from clinicians.models import Clinician, Credential
from patients.models import Patient
from routing.models import RoutePlan
from scheduling.tasks import optimize_day
from tenancy.models import Tenant
from visits.models import Visit, VisitStatus


@pytest.fixture
def optimize_day_fixture(db):
    tenant = Tenant.objects.create(name="Westside", timezone="UTC")
    u_rn = User.objects.create_user(
        email="rn@x.demo", password="p", tenant=tenant, role=Role.CLINICIAN
    )
    u_ma = User.objects.create_user(
        email="ma@x.demo", password="p", tenant=tenant, role=Role.CLINICIAN
    )
    rn = Clinician.objects.create(
        user=u_rn,
        tenant=tenant,
        credential=Credential.RN,
        home_lat=34.0,
        home_lon=-118.0,
    )
    ma = Clinician.objects.create(
        user=u_ma,
        tenant=tenant,
        credential=Credential.MA,
        home_lat=34.1,
        home_lon=-118.1,
    )
    the_day = date(2026, 4, 24)
    day_start = datetime(2026, 4, 24, 8, 0, tzinfo=UTC)
    # Two MA-required visits (both clinicians can do them) + one RN-required
    # visit (only RN can do it). Windowed so the order is feasible for each
    # clinician.
    visits: list[Visit] = []
    for i, skill in enumerate([Credential.MA, Credential.MA, Credential.RN]):
        p = Patient.objects.create(
            tenant=tenant,
            name=f"P{i}",
            phone="+1",
            address="x",
            lat=34.0 + 0.01 * (i + 1),
            lon=-118.0,
            required_skill=skill,
        )
        v = Visit.objects.create(
            tenant=tenant,
            patient=p,
            window_start=day_start + timedelta(hours=i),
            window_end=day_start + timedelta(hours=i + 4),
            required_skill=skill,
        )
        visits.append(v)
    return tenant, the_day, [rn, ma], visits


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
def test_optimize_day_creates_route_plan_per_clinician_with_non_empty_visits(
    optimize_day_fixture,
):
    tenant, the_day, _, _ = optimize_day_fixture
    result = optimize_day.delay(tenant.id, the_day.isoformat(), time_budget_s=1).get(timeout=15)
    plans = list(RoutePlan.objects.filter(tenant=tenant, date=the_day))
    assert result["routes"] >= 1
    assert len(plans) == result["routes"]
    for plan in plans:
        assert plan.visits_ordered, "route plan must carry visit ids"
        assert plan.solver_metadata.get("solver_version")


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
def test_optimize_day_stamps_visits_with_clinician_and_ordering_seq(
    optimize_day_fixture,
):
    tenant, the_day, _, visits = optimize_day_fixture
    optimize_day.delay(tenant.id, the_day.isoformat(), time_budget_s=1).get(timeout=15)
    # Re-read all visits.
    updated = {v.id: Visit.objects.get(id=v.id) for v in visits}
    assigned = [v for v in updated.values() if v.clinician_id is not None]
    assert assigned, "at least one visit should have been assigned"
    for v in assigned:
        assert v.ordering_seq is not None


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
def test_optimize_day_is_idempotent_under_re_run(optimize_day_fixture):
    tenant, the_day, _, _ = optimize_day_fixture
    first = optimize_day.delay(tenant.id, the_day.isoformat(), time_budget_s=1).get(timeout=15)
    count_after_first = RoutePlan.objects.filter(tenant=tenant, date=the_day).count()
    second = optimize_day.delay(tenant.id, the_day.isoformat(), time_budget_s=1).get(timeout=15)
    count_after_second = RoutePlan.objects.filter(tenant=tenant, date=the_day).count()
    assert count_after_first == count_after_second
    assert first["routes"] == second["routes"]


def test_optimize_day_resets_visits_when_status_changes_are_not_in_scope(
    optimize_day_fixture,
):
    # Already-completed visits must not be re-assigned. Marking one visit
    # COMPLETED before running optimize_day should leave it untouched.
    tenant, the_day, _, visits = optimize_day_fixture
    done = visits[0]
    done.status = VisitStatus.COMPLETED
    done.save()
    with override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True):
        optimize_day.delay(tenant.id, the_day.isoformat(), time_budget_s=1).get(timeout=15)
    refreshed = Visit.objects.get(id=done.id)
    assert refreshed.status == VisitStatus.COMPLETED
