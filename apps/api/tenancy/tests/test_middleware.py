from typing import cast

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import Role, User
from tenancy.models import Tenant


@pytest.mark.django_db
def test_request_tenant_is_set_from_jwt():
    tenant = Tenant.objects.create(name="Westside", timezone="UTC")
    user = User.objects.create_user(email="a@x.demo", password="p", tenant=tenant, role=Role.ADMIN)
    token = cast(RefreshToken, RefreshToken.for_user(user))
    token["tenant_id"] = tenant.id
    access = str(token.access_token)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    r = client.get("/api/v1/health")

    assert r.status_code == 200
    assert r.json()["tenant"] == "Westside"


@pytest.mark.django_db
def test_request_tenant_is_none_when_unauthenticated():
    client = APIClient()
    r = client.get("/api/v1/health")

    assert r.status_code == 200
    assert r.json()["tenant"] is None
