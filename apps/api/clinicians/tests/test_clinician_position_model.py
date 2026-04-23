from datetime import UTC, datetime, timedelta

import pytest

from accounts.models import Role, User
from clinicians.models import Clinician, ClinicianPosition, Credential
from tenancy.managers import clear_current_tenant, set_current_tenant
from tenancy.models import Tenant


@pytest.fixture
def clinician_in_tenant(db):
    tenant = Tenant.objects.create(name="Westside", timezone="UTC")
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
    return tenant, clinician


def test_latest_position_is_retrievable_via_ts_desc(clinician_in_tenant):
    tenant, clinician = clinician_in_tenant
    base = datetime(2026, 4, 23, 10, 0, tzinfo=UTC)
    for i in range(3):
        ClinicianPosition.objects.create(
            tenant=tenant,
            clinician=clinician,
            lat=34.0 + i * 0.01,
            lon=-118.0,
            ts=base + timedelta(minutes=i),
        )

    latest = ClinicianPosition.objects.filter(clinician=clinician).order_by("-ts").first()
    assert latest is not None
    assert latest.lat == pytest.approx(34.02)


def test_scoped_manager_filters_positions_by_tenant(clinician_in_tenant):
    tenant, clinician = clinician_in_tenant
    other_tenant = Tenant.objects.create(name="Other", timezone="UTC")
    other_user = User.objects.create_user(
        email="b@x.demo", password="p", tenant=other_tenant, role=Role.CLINICIAN
    )
    other_clinician = Clinician.objects.create(
        user=other_user,
        tenant=other_tenant,
        credential=Credential.RN,
        home_lat=0,
        home_lon=0,
    )
    now = datetime(2026, 4, 23, 10, 0, tzinfo=UTC)
    ClinicianPosition.objects.create(tenant=tenant, clinician=clinician, lat=0, lon=0, ts=now)
    ClinicianPosition.objects.create(
        tenant=other_tenant, clinician=other_clinician, lat=0, lon=0, ts=now
    )

    set_current_tenant(tenant)
    try:
        assert ClinicianPosition.scoped.count() == 1
    finally:
        clear_current_tenant()
