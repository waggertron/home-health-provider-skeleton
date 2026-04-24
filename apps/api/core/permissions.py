"""Role-based DRF permission classes.

Phase 2 Role model:
- admin and scheduler: full operational access inside own tenant.
- clinician: only writes its own data (own visits, own positions).
"""

from rest_framework.permissions import BasePermission

from accounts.models import Role


class IsSchedulerOrAdmin(BasePermission):
    message = "Requires scheduler or admin role."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "role", None) in {Role.ADMIN, Role.SCHEDULER}
        )


class IsClinician(BasePermission):
    message = "Requires clinician role."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user and user.is_authenticated and getattr(user, "role", None) == Role.CLINICIAN
        )
