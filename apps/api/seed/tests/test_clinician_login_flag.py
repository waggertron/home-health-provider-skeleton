"""Phase 6 T6 / Phase 9: --enable-clinician-login enables every clinician.

Originally only c00 got a usable password; switched to all clinicians so
the demo loop's smoke test can pick whichever clinician the VRP solver
actually assigned visits to.
"""

import pytest
from django.contrib.auth import authenticate
from django.core.management import call_command

from accounts.models import Role, User
from tenancy.models import Tenant


@pytest.mark.django_db
def test_seed_without_flag_leaves_clinician_passwords_unusable():
    call_command("seed_demo", "--idempotent")
    westside = Tenant.objects.get(name="Westside Home Health")
    for user in User.objects.filter(tenant=westside, role=Role.CLINICIAN):
        assert not user.has_usable_password()


@pytest.mark.django_db
def test_seed_with_flag_enables_login_for_every_clinician_per_tenant():
    call_command("seed_demo", "--idempotent", "--enable-clinician-login")
    westside = Tenant.objects.get(name="Westside Home Health")
    sunset = Tenant.objects.get(name="Sunset Hospice")

    for tenant in (westside, sunset):
        clinicians = User.objects.filter(tenant=tenant, role=Role.CLINICIAN)
        assert clinicians.count() >= 25
        for user in clinicians:
            assert user.has_usable_password(), user.email

    auth = authenticate(username="c00@westside.demo", password="demo1234")
    assert auth is not None
    auth = authenticate(username="c10@westside.demo", password="demo1234")
    assert auth is not None


@pytest.mark.django_db
def test_seed_flag_does_not_change_admin_passwords():
    """Admin accounts already log in with demo1234; flag should not regress them."""
    call_command("seed_demo", "--idempotent", "--enable-clinician-login")
    auth = authenticate(username="admin@westside.demo", password="demo1234")
    assert auth is not None
