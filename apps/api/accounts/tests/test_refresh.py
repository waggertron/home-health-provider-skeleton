import pytest
from rest_framework.test import APIClient

from accounts.models import Role, User
from tenancy.models import Tenant


@pytest.fixture
def login_tokens(db):
    tenant = Tenant.objects.create(name="Westside", timezone="UTC")
    User.objects.create_user(email="a@x.demo", password="p", tenant=tenant, role=Role.ADMIN)
    client = APIClient()
    r = client.post("/api/v1/auth/login", {"email": "a@x.demo", "password": "p"}, format="json")
    return r.json()


def test_refresh_returns_new_access(login_tokens):
    client = APIClient()
    r = client.post("/api/v1/auth/refresh", {"refresh": login_tokens["refresh"]}, format="json")
    assert r.status_code == 200
    assert "access" in r.json()


@pytest.mark.django_db
def test_refresh_invalid_token_is_401():
    client = APIClient()
    r = client.post("/api/v1/auth/refresh", {"refresh": "garbage"}, format="json")
    assert r.status_code == 401
