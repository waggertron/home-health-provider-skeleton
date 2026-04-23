from django.db import models

from clinicians.models import Clinician
from patients.models import Patient
from tenancy.managers import TenantScopedManager
from tenancy.models import Tenant


class VisitStatus(models.TextChoices):
    SCHEDULED = "scheduled", "Scheduled"
    ASSIGNED = "assigned", "Assigned"
    EN_ROUTE = "en_route", "En route"
    ON_SITE = "on_site", "On site"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"
    MISSED = "missed", "Missed"


class Visit(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="visits")
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="visits")
    clinician = models.ForeignKey(
        Clinician, on_delete=models.SET_NULL, null=True, blank=True, related_name="visits"
    )
    window_start = models.DateTimeField()
    window_end = models.DateTimeField()
    required_skill = models.CharField(max_length=32)
    status = models.CharField(
        max_length=16, choices=VisitStatus.choices, default=VisitStatus.SCHEDULED
    )
    check_in_at = models.DateTimeField(null=True, blank=True)
    check_out_at = models.DateTimeField(null=True, blank=True)
    ordering_seq = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    patient_confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()
    scoped = TenantScopedManager()

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(window_end__gt=models.F("window_start")),
                name="visit_window_end_after_start",
            ),
        ]

    def __str__(self) -> str:
        return f"Visit({self.patient.name}, {self.status})"
