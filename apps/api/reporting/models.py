from django.db import models

from clinicians.models import Clinician
from tenancy.managers import TenantScopedManager
from tenancy.models import Tenant


class DailyClinicianStats(models.Model):
    """Per-clinician day rollup.

    Populated only by reporting.rollup_daily. Never touched by request-path
    code. The (tenant, clinician, date) tuple is unique so the rollup task
    can use update_or_create idempotently.
    """

    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="daily_clinician_stats"
    )
    clinician = models.ForeignKey(Clinician, on_delete=models.CASCADE, related_name="daily_stats")
    date = models.DateField()
    visits_completed = models.IntegerField(default=0)
    on_time_count = models.IntegerField(default=0)
    late_count = models.IntegerField(default=0)
    total_drive_seconds = models.IntegerField(default=0)
    total_on_site_seconds = models.IntegerField(default=0)
    rolled_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()
    scoped = TenantScopedManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "clinician", "date"],
                name="uniq_daily_clinician_stats_tenant_clinician_date",
            ),
        ]
        indexes = [models.Index(fields=["tenant", "date"])]

    def __str__(self) -> str:
        return f"DailyClinicianStats({self.clinician_id}, {self.date})"


class DailyAgencyStats(models.Model):
    """Per-tenant day rollup."""

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="daily_agency_stats")
    date = models.DateField()
    visits_completed = models.IntegerField(default=0)
    missed_count = models.IntegerField(default=0)
    on_time_pct = models.FloatField(default=0.0)
    sms_sent = models.IntegerField(default=0)
    sms_delivered = models.IntegerField(default=0)
    rolled_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()
    scoped = TenantScopedManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "date"],
                name="uniq_daily_agency_stats_tenant_date",
            ),
        ]

    def __str__(self) -> str:
        return f"DailyAgencyStats({self.tenant_id}, {self.date})"
