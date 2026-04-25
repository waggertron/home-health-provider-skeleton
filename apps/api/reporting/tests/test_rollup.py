"""rollup_daily aggregates yesterday's COMPLETED visits per clinician + per tenant."""

from datetime import UTC, date, datetime, timedelta
from io import StringIO

import pytest
from django.core.management import call_command

from accounts.models import Role, User
from clinicians.models import Clinician, Credential
from messaging.models import SmsOutbox
from patients.models import Patient
from reporting.models import DailyAgencyStats, DailyClinicianStats
from reporting.rollup import rollup_daily
from tenancy.models import Tenant
from visits.models import Visit, VisitStatus


@pytest.fixture
def two_tenants_with_visits(db):
    """Two tenants, one clinician each, a few completed visits for 2026-04-23."""
    target = date(2026, 4, 23)
    day_start = datetime(2026, 4, 23, 9, 0, tzinfo=UTC)

    def _make_tenant(name: str) -> tuple[Tenant, Clinician, Patient]:
        tenant = Tenant.objects.create(name=name, timezone="UTC")
        u = User.objects.create_user(
            email=f"rn@{name}.demo", password="p", tenant=tenant, role=Role.CLINICIAN
        )
        c = Clinician.objects.create(
            user=u, tenant=tenant, credential=Credential.RN, home_lat=0, home_lon=0
        )
        p = Patient.objects.create(
            tenant=tenant,
            name=f"P-{name}",
            phone="+1",
            address="x",
            lat=0,
            lon=0,
            required_skill=Credential.RN,
        )
        return tenant, c, p

    westside, w_clinician, w_patient = _make_tenant("westside")
    sunset, s_clinician, s_patient = _make_tenant("sunset")

    # Westside: 1 on-time visit, 1 late visit, 1 missed.
    on_time_start = day_start  # 09:00
    Visit.objects.create(
        tenant=westside,
        patient=w_patient,
        clinician=w_clinician,
        window_start=on_time_start,
        window_end=on_time_start + timedelta(hours=1),
        required_skill=Credential.RN,
        status=VisitStatus.COMPLETED,
        check_in_at=on_time_start + timedelta(minutes=5),  # 5 min after start = on-time
        check_out_at=on_time_start + timedelta(minutes=35),  # 30 min on-site
    )
    late_start = day_start + timedelta(hours=2)  # 11:00
    Visit.objects.create(
        tenant=westside,
        patient=w_patient,
        clinician=w_clinician,
        window_start=late_start,
        window_end=late_start + timedelta(hours=1),
        required_skill=Credential.RN,
        status=VisitStatus.COMPLETED,
        check_in_at=late_start + timedelta(minutes=30),  # 30 min late
        check_out_at=late_start + timedelta(minutes=50),
    )
    missed_start = day_start + timedelta(hours=4)  # 13:00
    Visit.objects.create(
        tenant=westside,
        patient=w_patient,
        clinician=w_clinician,
        window_start=missed_start,
        window_end=missed_start + timedelta(hours=1),
        required_skill=Credential.RN,
        status=VisitStatus.MISSED,
    )
    sms = SmsOutbox.objects.create(
        tenant=westside,
        patient=w_patient,
        template="reminder",
        body="hi",
        status="delivered",
    )
    # auto_now_add stamps created_at at insert; backdate via .update() so the
    # rollup's date-bounded query catches it.
    SmsOutbox.objects.filter(pk=sms.pk).update(created_at=day_start)

    # Sunset: 1 completed visit on-time.
    Visit.objects.create(
        tenant=sunset,
        patient=s_patient,
        clinician=s_clinician,
        window_start=day_start,
        window_end=day_start + timedelta(hours=1),
        required_skill=Credential.RN,
        status=VisitStatus.COMPLETED,
        check_in_at=day_start + timedelta(minutes=2),
        check_out_at=day_start + timedelta(minutes=30),
    )

    return target, westside, w_clinician, sunset, s_clinician


def test_rollup_creates_one_clinician_row_per_tenant_clinician(two_tenants_with_visits):
    target, westside, w_clinician, sunset, s_clinician = two_tenants_with_visits
    summary = rollup_daily(target)
    assert summary["clinician_rows"] == 2
    assert summary["agency_rows"] == 2
    w_row = DailyClinicianStats.objects.get(tenant=westside, clinician=w_clinician, date=target)
    s_row = DailyClinicianStats.objects.get(tenant=sunset, clinician=s_clinician, date=target)
    assert w_row.visits_completed == 2
    assert s_row.visits_completed == 1


def test_rollup_classifies_on_time_vs_late(two_tenants_with_visits):
    target, westside, w_clinician, _, _ = two_tenants_with_visits
    rollup_daily(target)
    row = DailyClinicianStats.objects.get(tenant=westside, clinician=w_clinician, date=target)
    assert row.on_time_count == 1
    assert row.late_count == 1


def test_rollup_agency_stats_capture_missed_and_on_time_pct(two_tenants_with_visits):
    target, westside, _, _, _ = two_tenants_with_visits
    rollup_daily(target)
    agg = DailyAgencyStats.objects.get(tenant=westside, date=target)
    assert agg.visits_completed == 2
    assert agg.missed_count == 1
    # 1 on-time of 2 → 0.5
    assert agg.on_time_pct == pytest.approx(0.5)
    assert agg.sms_sent == 1
    assert agg.sms_delivered == 1


def test_rollup_is_idempotent(two_tenants_with_visits):
    target, westside, w_clinician, _, _ = two_tenants_with_visits
    rollup_daily(target)
    first_count = DailyClinicianStats.objects.count()
    rollup_daily(target)
    assert DailyClinicianStats.objects.count() == first_count
    row = DailyClinicianStats.objects.get(tenant=westside, clinician=w_clinician, date=target)
    assert row.visits_completed == 2


def test_rollup_scoped_to_one_tenant(two_tenants_with_visits):
    target, westside, _, sunset, _ = two_tenants_with_visits
    rollup_daily(target, tenant_id=westside.id)
    assert DailyAgencyStats.objects.filter(tenant=westside).count() == 1
    assert DailyAgencyStats.objects.filter(tenant=sunset).count() == 0


def test_rollup_management_command_passes_args_through(two_tenants_with_visits):
    target, _, _, _, _ = two_tenants_with_visits
    out = StringIO()
    call_command("rollup", "--date", target.isoformat(), stdout=out)
    assert "Rollup complete" in out.getvalue()
    assert DailyAgencyStats.objects.count() == 2
