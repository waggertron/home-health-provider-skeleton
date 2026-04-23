import pytest

from clinicians.models import Credential
from messaging.models import SmsOutbox, SmsStatus
from patients.models import Patient
from tenancy.managers import clear_current_tenant, set_current_tenant
from tenancy.models import Tenant


@pytest.mark.django_db
def test_sms_defaults_to_queued_and_nullable_patient_visit():
    tenant = Tenant.objects.create(name="T", timezone="UTC")
    sms = SmsOutbox.objects.create(
        tenant=tenant,
        template="visit_arrival",
        body="Your clinician is on the way.",
    )
    assert sms.status == SmsStatus.QUEUED
    assert sms.delivered_at is None
    assert sms.patient is None
    assert sms.visit is None


@pytest.mark.django_db
def test_sms_can_link_to_patient_and_visit():
    tenant = Tenant.objects.create(name="T", timezone="UTC")
    patient = Patient.objects.create(
        tenant=tenant,
        name="Jane",
        phone="+1",
        address="x",
        lat=0,
        lon=0,
        required_skill=Credential.RN,
    )
    sms = SmsOutbox.objects.create(
        tenant=tenant,
        patient=patient,
        template="visit_arrival",
        body="Hi Jane!",
    )
    assert sms.patient_id == patient.id


@pytest.mark.django_db
def test_scoped_manager_filters_sms_by_tenant():
    t1 = Tenant.objects.create(name="T1", timezone="UTC")
    t2 = Tenant.objects.create(name="T2", timezone="UTC")
    SmsOutbox.objects.create(tenant=t1, template="x", body="y")
    SmsOutbox.objects.create(tenant=t2, template="x", body="y")

    set_current_tenant(t1)
    try:
        assert SmsOutbox.scoped.count() == 1
    finally:
        clear_current_tenant()
