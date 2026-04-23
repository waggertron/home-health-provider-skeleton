import pytest
from django.db import IntegrityError

from tenancy.models import Tenant


@pytest.mark.django_db
def test_tenant_is_created_with_name_and_timezone():
    tenant = Tenant.objects.create(
        name="Westside Home Health",
        timezone="America/Los_Angeles",
    )
    assert tenant.id is not None
    assert str(tenant) == "Westside Home Health"
    assert tenant.timezone == "America/Los_Angeles"


@pytest.mark.django_db
def test_tenant_name_is_unique():
    Tenant.objects.create(name="Westside Home Health", timezone="America/Los_Angeles")
    with pytest.raises(IntegrityError):
        Tenant.objects.create(name="Westside Home Health", timezone="America/Los_Angeles")


@pytest.mark.django_db
def test_tenant_home_base_coords_default_to_null():
    tenant = Tenant.objects.create(name="Sunset Hospice", timezone="America/Los_Angeles")
    assert tenant.home_base_lat is None
    assert tenant.home_base_lon is None
