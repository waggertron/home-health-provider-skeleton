import pytest
from django.db import IntegrityError

from accounts.models import Role, User
from tenancy.models import Tenant


@pytest.mark.django_db
def test_create_user_with_tenant_and_role():
    tenant = Tenant.objects.create(name="Westside", timezone="America/Los_Angeles")
    user = User.objects.create_user(
        email="admin@westside.demo",
        password="demo1234",
        tenant=tenant,
        role=Role.ADMIN,
    )
    assert user.pk is not None
    assert user.tenant_id == tenant.id
    assert user.role == Role.ADMIN
    assert user.check_password("demo1234")
    assert user.is_active


@pytest.mark.django_db
def test_email_is_unique_within_tenant():
    tenant = Tenant.objects.create(name="W", timezone="UTC")
    User.objects.create_user(
        email="a@x.demo", password="p", tenant=tenant, role=Role.CLINICIAN
    )
    with pytest.raises(IntegrityError):
        User.objects.create_user(
            email="a@x.demo", password="p", tenant=tenant, role=Role.CLINICIAN
        )


@pytest.mark.django_db
def test_same_email_is_allowed_across_tenants():
    t1 = Tenant.objects.create(name="T1", timezone="UTC")
    t2 = Tenant.objects.create(name="T2", timezone="UTC")
    User.objects.create_user(email="a@x.demo", password="p", tenant=t1, role=Role.CLINICIAN)
    # Should not raise.
    User.objects.create_user(email="a@x.demo", password="p", tenant=t2, role=Role.CLINICIAN)


@pytest.mark.django_db
def test_create_user_requires_email():
    tenant = Tenant.objects.create(name="T", timezone="UTC")
    with pytest.raises(ValueError):
        User.objects.create_user(email="", password="p", tenant=tenant, role=Role.CLINICIAN)
