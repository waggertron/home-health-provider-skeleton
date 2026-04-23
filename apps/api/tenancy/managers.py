from contextvars import ContextVar

from django.db import models

from tenancy.models import Tenant

_current_tenant: ContextVar[Tenant | None] = ContextVar("_current_tenant", default=None)


def set_current_tenant(tenant: Tenant | None) -> None:
    _current_tenant.set(tenant)


def clear_current_tenant() -> None:
    _current_tenant.set(None)


def current_tenant() -> Tenant | None:
    return _current_tenant.get()


class TenantScopedQuerySet(models.QuerySet):
    def for_current_tenant(self) -> "TenantScopedQuerySet":
        t = current_tenant()
        if t is None:
            return self.none()
        return self.filter(tenant=t)


class TenantScopedManager(models.Manager.from_queryset(TenantScopedQuerySet)):  # type: ignore[misc]
    """Manager that returns rows for the current tenant only, or nothing when unset.

    Fails closed: if no tenant is in context, queries return an empty queryset.
    Use the default `.objects` manager for admin scripts and auth lookups that
    legitimately need to cross tenants.
    """

    def get_queryset(self) -> TenantScopedQuerySet:
        qs: TenantScopedQuerySet = super().get_queryset()
        return qs.for_current_tenant()
