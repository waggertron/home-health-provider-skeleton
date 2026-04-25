from datetime import date

import pytest
from django.db import IntegrityError

from accounts.models import Role, User
from clinicians.models import Clinician, Credential
from reporting.models import DailyAgencyStats, DailyClinicianStats
from tenancy.models import Tenant


@pytest.fixture
def tenant_with_clinician(db):
    tenant = Tenant.objects.create(name="Westside", timezone="UTC")
    user = User.objects.create_user(
        email="rn@x.demo", password="p", tenant=tenant, role=Role.CLINICIAN
    )
    clinician = Clinician.objects.create(
        user=user, tenant=tenant, credential=Credential.RN, home_lat=0, home_lon=0
    )
    return tenant, clinician


def test_daily_clinician_stats_default_zeros(tenant_with_clinician):
    tenant, clinician = tenant_with_clinician
    row = DailyClinicianStats.objects.create(
        tenant=tenant, clinician=clinician, date=date(2026, 4, 24)
    )
    assert row.visits_completed == 0
    assert row.on_time_count == 0
    assert row.total_drive_seconds == 0


def test_daily_clinician_stats_unique_per_tenant_clinician_date(tenant_with_clinician):
    tenant, clinician = tenant_with_clinician
    DailyClinicianStats.objects.create(tenant=tenant, clinician=clinician, date=date(2026, 4, 24))
    with pytest.raises(IntegrityError):
        DailyClinicianStats.objects.create(
            tenant=tenant, clinician=clinician, date=date(2026, 4, 24)
        )


def test_daily_agency_stats_unique_per_tenant_date(tenant_with_clinician):
    tenant, _ = tenant_with_clinician
    DailyAgencyStats.objects.create(tenant=tenant, date=date(2026, 4, 24))
    with pytest.raises(IntegrityError):
        DailyAgencyStats.objects.create(tenant=tenant, date=date(2026, 4, 24))


def test_str_includes_id_and_date(tenant_with_clinician):
    tenant, clinician = tenant_with_clinician
    row = DailyClinicianStats.objects.create(
        tenant=tenant, clinician=clinician, date=date(2026, 4, 24)
    )
    assert str(clinician.id) in str(row)
    assert "2026-04-24" in str(row)
