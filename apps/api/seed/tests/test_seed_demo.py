import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from accounts.models import Role, User
from clinicians.models import Clinician
from patients.models import Patient
from seed.management.commands.seed_demo import (
    CLINICIANS_PER_TENANT,
    HISTORY_PER_TENANT,
    PATIENTS_PER_TENANT,
    TODAY_VISITS_PER_TENANT,
)
from tenancy.models import Tenant
from visits.models import Visit, VisitStatus


@pytest.mark.django_db
def test_seed_demo_creates_two_tenants_and_admins():
    call_command("seed_demo", "--idempotent")

    assert Tenant.objects.count() == 2
    names = sorted(Tenant.objects.values_list("name", flat=True))
    assert names == ["Sunset Hospice", "Westside Home Health"]
    assert User.objects.filter(email="admin@westside.demo", role=Role.ADMIN).exists()
    assert User.objects.filter(email="admin@sunset.demo", role=Role.ADMIN).exists()


@pytest.mark.django_db
def test_seed_demo_creates_expected_phase_3_data_counts():
    call_command("seed_demo", "--idempotent")

    tenants = list(Tenant.objects.all())
    assert len(tenants) == 2
    for t in tenants:
        assert Clinician.objects.filter(tenant=t).count() == CLINICIANS_PER_TENANT
        assert Patient.objects.filter(tenant=t).count() == PATIENTS_PER_TENANT
        assert (
            Visit.objects.filter(tenant=t, status=VisitStatus.COMPLETED).count()
            == HISTORY_PER_TENANT
        )
        # Today-visits are created fresh at SCHEDULED.
        assert (
            Visit.objects.filter(tenant=t, status=VisitStatus.SCHEDULED).count()
            == TODAY_VISITS_PER_TENANT
        )
    # 1 admin + 25 clinicians per tenant.
    assert User.objects.count() == 2 * (1 + CLINICIANS_PER_TENANT)


@pytest.mark.django_db
def test_seed_demo_is_idempotent_across_full_stack():
    call_command("seed_demo", "--idempotent")
    clinician_count = Clinician.objects.count()
    patient_count = Patient.objects.count()
    visit_count = Visit.objects.count()
    user_count = User.objects.count()

    call_command("seed_demo", "--idempotent")

    assert Clinician.objects.count() == clinician_count
    assert Patient.objects.count() == patient_count
    assert Visit.objects.count() == visit_count
    assert User.objects.count() == user_count


@pytest.mark.django_db
def test_seed_demo_force_wipes_and_reseeds():
    call_command("seed_demo", "--idempotent")
    Tenant.objects.filter(name="Westside Home Health").update(timezone="UTC")
    call_command("seed_demo", "--force")

    assert Tenant.objects.get(name="Westside Home Health").timezone == "America/Los_Angeles"
    assert Tenant.objects.count() == 2
    # After --force everything gets re-created at Phase 3 scale.
    assert Clinician.objects.count() == 2 * CLINICIANS_PER_TENANT
    assert Patient.objects.count() == 2 * PATIENTS_PER_TENANT


@pytest.mark.django_db
def test_seeded_admin_can_login():
    call_command("seed_demo", "--idempotent")

    client = APIClient()
    r = client.post(
        "/api/v1/auth/login",
        {"email": "admin@westside.demo", "password": "demo1234"},
        format="json",
    )
    assert r.status_code == 200
    assert "access" in r.json()
