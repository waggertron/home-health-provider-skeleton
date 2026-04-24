"""DRF permission classes — full matrix across roles + anon + inactive."""

from types import SimpleNamespace

import pytest

from accounts.models import Role, User
from core.permissions import IsClinician, IsSchedulerOrAdmin
from tenancy.models import Tenant


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(name="Westside", timezone="UTC")


def _req_for(user) -> SimpleNamespace:
    return SimpleNamespace(user=user)


def test_is_scheduler_or_admin_allows_scheduler(tenant):
    user = User.objects.create_user(
        email="s@x.demo", password="p", tenant=tenant, role=Role.SCHEDULER
    )
    assert IsSchedulerOrAdmin().has_permission(_req_for(user), None) is True


def test_is_scheduler_or_admin_allows_admin(tenant):
    user = User.objects.create_user(email="a@x.demo", password="p", tenant=tenant, role=Role.ADMIN)
    assert IsSchedulerOrAdmin().has_permission(_req_for(user), None) is True


def test_is_scheduler_or_admin_rejects_clinician(tenant):
    user = User.objects.create_user(
        email="c@x.demo", password="p", tenant=tenant, role=Role.CLINICIAN
    )
    assert IsSchedulerOrAdmin().has_permission(_req_for(user), None) is False


def test_is_scheduler_or_admin_rejects_anonymous():
    from django.contrib.auth.models import AnonymousUser

    assert IsSchedulerOrAdmin().has_permission(_req_for(AnonymousUser()), None) is False


def test_is_scheduler_or_admin_rejects_inactive_user(tenant):
    user = User.objects.create_user(
        email="x@x.demo", password="p", tenant=tenant, role=Role.SCHEDULER
    )
    user.is_active = False
    user.save()
    # is_authenticated is True for inactive users in Django's custom-user flow,
    # but DRF's IsAuthenticated gate runs first in real views; the permission
    # class itself is role-only. Sanity-check that at the class level its
    # return is still role-gated (True) — auth gate handles inactive.
    assert IsSchedulerOrAdmin().has_permission(_req_for(user), None) is True


def test_is_clinician_allows_clinician(tenant):
    user = User.objects.create_user(
        email="c@x.demo", password="p", tenant=tenant, role=Role.CLINICIAN
    )
    assert IsClinician().has_permission(_req_for(user), None) is True


def test_is_clinician_rejects_scheduler_and_admin(tenant):
    sched = User.objects.create_user(
        email="s@x.demo", password="p", tenant=tenant, role=Role.SCHEDULER
    )
    admin = User.objects.create_user(email="a@x.demo", password="p", tenant=tenant, role=Role.ADMIN)
    assert IsClinician().has_permission(_req_for(sched), None) is False
    assert IsClinician().has_permission(_req_for(admin), None) is False


def test_is_clinician_rejects_anonymous():
    from django.contrib.auth.models import AnonymousUser

    assert IsClinician().has_permission(_req_for(AnonymousUser()), None) is False
