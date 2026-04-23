from django.contrib.auth.models import AbstractBaseUser
from django.db import models

from tenancy.managers import TenantScopedManager
from tenancy.models import Tenant

from .managers import UserManager


class Role(models.TextChoices):
    ADMIN = "admin", "Admin"
    SCHEDULER = "scheduler", "Scheduler"
    CLINICIAN = "clinician", "Clinician"


class User(AbstractBaseUser):
    email = models.EmailField()
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="users")
    role = models.CharField(max_length=16, choices=Role.choices)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()
    scoped = TenantScopedManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "email"], name="uniq_user_email_per_tenant"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.email} ({self.tenant.name})"
