import pytest

from clinicians.models import Credential
from patients.models import Patient
from tenancy.managers import clear_current_tenant, set_current_tenant
from tenancy.models import Tenant


@pytest.mark.django_db
def test_patient_requires_tenant_and_core_fields():
    tenant = Tenant.objects.create(name="Westside", timezone="UTC")
    p = Patient.objects.create(
        tenant=tenant,
        name="Jane Doe",
        phone="+13105551234",
        address="123 Ocean Ave, Santa Monica, CA",
        lat=34.01,
        lon=-118.49,
        required_skill=Credential.RN,
    )
    assert p.id is not None
    assert str(p) == "Jane Doe (Westside)"


@pytest.mark.django_db
def test_patient_preferences_defaults_to_empty_dict():
    tenant = Tenant.objects.create(name="T", timezone="UTC")
    p = Patient.objects.create(
        tenant=tenant,
        name="J",
        phone="+1",
        address="x",
        lat=0,
        lon=0,
        required_skill=Credential.MA,
    )
    assert p.preferences == {}


@pytest.mark.django_db
def test_scoped_manager_filters_patients_by_current_tenant():
    t1 = Tenant.objects.create(name="T1", timezone="UTC")
    t2 = Tenant.objects.create(name="T2", timezone="UTC")
    for t in (t1, t2):
        Patient.objects.create(
            tenant=t,
            name=f"P-{t.id}",
            phone="+1",
            address="x",
            lat=0,
            lon=0,
            required_skill=Credential.RN,
        )

    set_current_tenant(t1)
    try:
        assert Patient.scoped.count() == 1
    finally:
        clear_current_tenant()
