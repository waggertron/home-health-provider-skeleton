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
