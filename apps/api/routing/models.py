from django.db import models

from clinicians.models import Clinician
from tenancy.managers import TenantScopedManager
from tenancy.models import Tenant


class RoutePlan(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="route_plans")
    clinician = models.ForeignKey(Clinician, on_delete=models.CASCADE, related_name="route_plans")
    date = models.DateField()
    visits_ordered = models.JSONField(default=list, blank=True)
    solver_metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()
    scoped = TenantScopedManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "clinician", "date"],
                name="uniq_route_plan_per_tenant_clinician_date",
            ),
        ]

    def __str__(self) -> str:
        return f"RoutePlan({self.clinician}, {self.date})"
