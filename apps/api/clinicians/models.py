from django.db import models

from accounts.models import User
from tenancy.managers import TenantScopedManager
from tenancy.models import Tenant


class Credential(models.TextChoices):
    RN = "RN", "Registered Nurse"
    LVN = "LVN", "Licensed Vocational Nurse"
    MA = "MA", "Medical Assistant"
    PHLEBOTOMIST = "phlebotomist", "Phlebotomist"


class Clinician(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="clinician_profile")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="clinicians")
    credential = models.CharField(max_length=32, choices=Credential.choices)
    skills = models.JSONField(default=list, blank=True)
    home_lat = models.FloatField()
    home_lon = models.FloatField()
    shift_windows = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()
    scoped = TenantScopedManager()

    def __str__(self) -> str:
        return f"{self.user.email} ({self.credential})"


class ClinicianPosition(models.Model):
    """A GPS ping reported by a clinician's mobile app.

    Many per clinician per day; we keep them all for history and query the
    latest-per-clinician for the ops map. The composite index on
    (clinician_id, ts DESC) makes the latest-lookup fast.
    """

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="clinician_positions")
    clinician = models.ForeignKey(Clinician, on_delete=models.CASCADE, related_name="positions")
    lat = models.FloatField()
    lon = models.FloatField()
    ts = models.DateTimeField()
    heading = models.FloatField(null=True, blank=True)
    speed = models.FloatField(null=True, blank=True)

    objects = models.Manager()
    scoped = TenantScopedManager()

    class Meta:
        indexes = [
            models.Index(fields=["clinician", "-ts"], name="cpos_clinician_ts_desc"),
        ]

    def __str__(self) -> str:
        return f"Position({self.clinician}, {self.ts.isoformat()})"
