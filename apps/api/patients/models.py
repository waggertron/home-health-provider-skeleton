from django.db import models

from tenancy.managers import TenantScopedManager
from tenancy.models import Tenant


class Patient(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="patients")
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=32)
    address = models.CharField(max_length=500)
    lat = models.FloatField()
    lon = models.FloatField()
    required_skill = models.CharField(max_length=32)
    preferences = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()
    scoped = TenantScopedManager()

    def __str__(self) -> str:
        return f"{self.name} ({self.tenant.name})"
