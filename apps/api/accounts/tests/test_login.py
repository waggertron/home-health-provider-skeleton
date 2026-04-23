import pytest
from rest_framework.test import APIClient

from accounts.models import Role, User
from tenancy.models import Tenant


@pytest.fixture
def admin_user(db):
    tenant = Tenant.objects.create(name="Westside", timezone="UTC")
    return User.objects.create_user(
        email="admin@westside.demo", password="demo1234", tenant=tenant, role=Role.ADMIN
    )


def test_login_returns_access_and_refresh(admin_user):
    client = APIClient()
    r = client.post(
        "/api/v1/auth/login",
        {"email": "admin@westside.demo", "password": "demo1234"},
        format="json",
    )
    assert r.status_code == 200
    body = r.json()
    assert "access" in body and "refresh" in body
    assert body["user"]["email"] == "admin@westside.demo"
    assert body["user"]["role"] == "admin"
    assert body["user"]["tenant_id"] == admin_user.tenant_id


def test_login_wrong_password_is_401(admin_user):
    client = APIClient()
    r = client.post(
        "/api/v1/auth/login",
        {"email": "admin@westside.demo", "password": "wrong"},
        format="json",
    )
    assert r.status_code == 401


@pytest.mark.django_db
def test_login_unknown_email_is_401():
    client = APIClient()
    r = client.post(
        "/api/v1/auth/login",
        {"email": "nobody@x.demo", "password": "x"},
        format="json",
    )
    assert r.status_code == 401
