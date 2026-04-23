from datetime import date

import pytest
from django.db import IntegrityError

from accounts.models import Role, User
from clinicians.models import Clinician, Credential
from routing.models import RoutePlan
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


def test_route_plan_stores_ordered_visits_and_solver_metadata(clinician_in_tenant):
    tenant, clinician = clinician_in_tenant
    rp = RoutePlan.objects.create(
        tenant=tenant,
        clinician=clinician,
        date=date(2026, 4, 23),
        visits_ordered=[42, 17, 88],
        solver_metadata={"objective": 12345, "solve_ms": 320},
    )
    assert rp.visits_ordered == [42, 17, 88]
    assert rp.solver_metadata["objective"] == 12345


def test_route_plan_is_unique_per_tenant_clinician_date(clinician_in_tenant):
    tenant, clinician = clinician_in_tenant
    RoutePlan.objects.create(tenant=tenant, clinician=clinician, date=date(2026, 4, 23))
    with pytest.raises(IntegrityError):
        RoutePlan.objects.create(tenant=tenant, clinician=clinician, date=date(2026, 4, 23))


def test_scoped_manager_filters_route_plans_by_tenant(clinician_in_tenant):
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
    RoutePlan.objects.create(tenant=tenant, clinician=clinician, date=date(2026, 4, 23))
    RoutePlan.objects.create(tenant=other_tenant, clinician=other_clinician, date=date(2026, 4, 23))

    set_current_tenant(tenant)
    try:
        assert RoutePlan.scoped.count() == 1
    finally:
        clear_current_tenant()
