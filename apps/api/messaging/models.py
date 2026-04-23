from django.db import models

from patients.models import Patient
from tenancy.managers import TenantScopedManager
from tenancy.models import Tenant
from visits.models import Visit


class SmsStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    DELIVERED = "delivered", "Delivered"
    FAILED = "failed", "Failed"


class SmsOutbox(models.Model):
    """Simulated SMS messages — Phase 1 of the plan uses a DB row instead of Twilio.

    patient and visit are nullable so the table can later hold inquiry / contact-form
    messages from the marketing site as well as visit-related SMS.
    """

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="sms_outbox")
    patient = models.ForeignKey(
        Patient,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sms_messages",
    )
    visit = models.ForeignKey(
        Visit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sms_messages",
    )
    template = models.CharField(max_length=64)
    body = models.TextField()
    status = models.CharField(max_length=16, choices=SmsStatus.choices, default=SmsStatus.QUEUED)
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    inbound_reply = models.TextField(blank=True, default="")

    objects = models.Manager()
    scoped = TenantScopedManager()

    def __str__(self) -> str:
        return f"SMS({self.template}, {self.status})"
