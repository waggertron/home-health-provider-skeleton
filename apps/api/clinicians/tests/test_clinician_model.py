import pytest

from accounts.models import Role, User
from clinicians.models import Clinician, Credential
from tenancy.managers import clear_current_tenant, set_current_tenant
from tenancy.models import Tenant


@pytest.mark.django_db
def test_clinician_is_linked_to_a_user_and_tenant():
    tenant = Tenant.objects.create(name="Westside", timezone="UTC")
    user = User.objects.create_user(
        email="rn@x.demo", password="p", tenant=tenant, role=Role.CLINICIAN
    )
    c = Clinician.objects.create(
        user=user,
        tenant=tenant,
        credential=Credential.RN,
        home_lat=34.0,
        home_lon=-118.0,
    )
    assert c.tenant_id == tenant.id
    assert c.user_id == user.id
    assert str(c) == "rn@x.demo (RN)"


@pytest.mark.django_db
def test_credential_enum_accepts_standard_credentials():
    tenant = Tenant.objects.create(name="T", timezone="UTC")
    for cred in (Credential.RN, Credential.LVN, Credential.MA, Credential.PHLEBOTOMIST):
        user = User.objects.create_user(
            email=f"{cred.value}@x.demo",
            password="p",
            tenant=tenant,
            role=Role.CLINICIAN,
        )
        Clinician.objects.create(
            user=user,
            tenant=tenant,
            credential=cred,
            home_lat=0,
            home_lon=0,
        )
    assert Clinician.objects.count() == 4


@pytest.mark.django_db
def test_clinician_skills_and_shift_windows_default_to_empty_list():
    tenant = Tenant.objects.create(name="T", timezone="UTC")
    user = User.objects.create_user(
        email="a@x.demo", password="p", tenant=tenant, role=Role.CLINICIAN
    )
    c = Clinician.objects.create(
        user=user,
        tenant=tenant,
        credential=Credential.RN,
        home_lat=0,
        home_lon=0,
    )
    assert c.skills == []
    assert c.shift_windows == []


@pytest.mark.django_db
def test_scoped_manager_filters_clinicians_by_current_tenant():
    t1 = Tenant.objects.create(name="T1", timezone="UTC")
    t2 = Tenant.objects.create(name="T2", timezone="UTC")
    for t in (t1, t2):
        u = User.objects.create_user(
            email=f"a-{t.id}@x.demo",
            password="p",
            tenant=t,
            role=Role.CLINICIAN,
        )
        Clinician.objects.create(
            user=u,
            tenant=t,
            credential=Credential.RN,
            home_lat=0,
            home_lon=0,
        )

    set_current_tenant(t1)
    try:
        assert Clinician.scoped.count() == 1
    finally:
        clear_current_tenant()
