import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from accounts.models import User
from tenancy.models import Tenant


@pytest.mark.django_db
def test_seed_demo_creates_two_tenants_and_admins():
    call_command("seed_demo", "--idempotent")

    assert Tenant.objects.count() == 2
    names = sorted(Tenant.objects.values_list("name", flat=True))
    assert names == ["Sunset Hospice", "Westside Home Health"]
    assert User.objects.filter(email="admin@westside.demo").exists()
    assert User.objects.filter(email="admin@sunset.demo").exists()


@pytest.mark.django_db
def test_seed_demo_is_idempotent_on_repeat_runs():
    call_command("seed_demo", "--idempotent")
    call_command("seed_demo", "--idempotent")

    assert Tenant.objects.count() == 2
    assert User.objects.count() == 2


@pytest.mark.django_db
def test_seed_demo_force_wipes_and_reseeds():
    call_command("seed_demo", "--idempotent")
    Tenant.objects.filter(name="Westside Home Health").update(timezone="UTC")
    call_command("seed_demo", "--force")

    # After --force, timezone is restored to the canonical value.
    assert (
        Tenant.objects.get(name="Westside Home Health").timezone == "America/Los_Angeles"
    )
    assert Tenant.objects.count() == 2


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
