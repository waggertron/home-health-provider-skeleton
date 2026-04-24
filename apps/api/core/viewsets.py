"""Shared DRF viewset base that enforces tenancy on every request."""

from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied


class BaseTenantViewSet(viewsets.ModelViewSet):
    """ModelViewSet that stamps the caller's tenant onto new rows.

    Subclasses implement `get_queryset` themselves — typically returning
    `<Model>.scoped.all()` so the TenantScopedManager contextvar handles
    isolation. `perform_create` stamps `tenant` from the request onto
    created rows so API callers can't forge or omit it.
    """

    def perform_create(self, serializer) -> None:
        tenant = getattr(self.request, "tenant", None)
        if tenant is None:
            raise PermissionDenied("No tenant in context.")
        serializer.save(tenant=tenant)
