"""Shared DRF viewset base that enforces tenancy on every request."""

from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied


class BaseTenantViewSet(viewsets.ModelViewSet):
    """ModelViewSet that scopes queryset to the caller's tenant.

    Subclasses set `scoped_model` (a model with a TenantScopedManager on it
    named `.scoped`) and `serializer_class`. The queryset is always resolved
    via the model's `scoped` manager, which reads the current tenant from the
    contextvar set by tenancy.middleware.TenantMiddleware.

    On create, the caller's tenant is stamped onto the new row automatically.
    """

    scoped_model = None

    def get_queryset(self):
        if self.scoped_model is None:  # pragma: no cover — catches misconfiguration
            raise RuntimeError(f"{type(self).__name__} must set scoped_model")
        return self.scoped_model.scoped.all()

    def perform_create(self, serializer) -> None:
        tenant = getattr(self.request, "tenant", None)
        if tenant is None:
            raise PermissionDenied("No tenant in context.")
        serializer.save(tenant=tenant)
