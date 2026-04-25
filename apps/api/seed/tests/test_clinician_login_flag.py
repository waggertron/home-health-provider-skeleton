"""Phase 6 T6: --enable-clinician-login sets a usable password on c00@."""

import pytest
from django.contrib.auth import authenticate
from django.core.management import call_command

from accounts.models import User
from tenancy.models import Tenant


@pytest.mark.django_db
def test_seed_without_flag_leaves_clinician_password_unusable():
    call_command("seed_demo", "--idempotent")
    westside = Tenant.objects.get(name="Westside Home Health")
    user = User.objects.get(email="c00@westside.demo", tenant=westside)
    assert not user.has_usable_password()


@pytest.mark.django_db
def test_seed_with_flag_enables_login_for_first_clinician_per_tenant():
    call_command("seed_demo", "--idempotent", "--enable-clinician-login")
    westside = Tenant.objects.get(name="Westside Home Health")
    sunset = Tenant.objects.get(name="Sunset Hospice")

    westside_user = User.objects.get(email="c00@westside.demo", tenant=westside)
    sunset_user = User.objects.get(email="c00@sunset.demo", tenant=sunset)
    assert westside_user.has_usable_password()
    assert sunset_user.has_usable_password()
    # Confirm the password is the documented demo string.
    auth = authenticate(username="c00@westside.demo", password="demo1234")
    assert auth is not None


@pytest.mark.django_db
def test_seed_flag_only_enables_first_clinician_other_clinicians_stay_unusable():
    call_command("seed_demo", "--idempotent", "--enable-clinician-login")
    westside = Tenant.objects.get(name="Westside Home Health")
    other = User.objects.get(email="c01@westside.demo", tenant=westside)
    assert not other.has_usable_password()
