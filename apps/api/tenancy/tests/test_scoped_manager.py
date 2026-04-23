import pytest

from accounts.models import Role, User
from tenancy.managers import clear_current_tenant, set_current_tenant
from tenancy.models import Tenant


@pytest.mark.django_db
def test_scoped_queryset_filters_by_current_tenant():
    t1 = Tenant.objects.create(name="T1", timezone="UTC")
    t2 = Tenant.objects.create(name="T2", timezone="UTC")
    User.objects.create_user(email="a@x.demo", password="p", tenant=t1, role=Role.ADMIN)
    User.objects.create_user(email="b@x.demo", password="p", tenant=t2, role=Role.ADMIN)

    set_current_tenant(t1)
    try:
        emails = sorted(User.scoped.values_list("email", flat=True))
        assert emails == ["a@x.demo"]
    finally:
        clear_current_tenant()


@pytest.mark.django_db
def test_unscoped_manager_returns_all_rows():
    t1 = Tenant.objects.create(name="T1", timezone="UTC")
    t2 = Tenant.objects.create(name="T2", timezone="UTC")
    User.objects.create_user(email="a@x.demo", password="p", tenant=t1, role=Role.ADMIN)
    User.objects.create_user(email="b@x.demo", password="p", tenant=t2, role=Role.ADMIN)

    # Without setting current tenant, the default manager returns everything;
    # this is intentional so admin scripts and auth backend can look up across tenants.
    assert User.objects.count() == 2


@pytest.mark.django_db
def test_scoped_manager_returns_empty_when_no_current_tenant():
    t1 = Tenant.objects.create(name="T1", timezone="UTC")
    User.objects.create_user(email="a@x.demo", password="p", tenant=t1, role=Role.ADMIN)

    # scoped manager without a current tenant should fail closed (return nothing)
    # to prevent accidental leakage.
    clear_current_tenant()
    assert User.scoped.count() == 0
