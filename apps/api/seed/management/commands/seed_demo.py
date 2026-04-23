"""Seed demo tenants and accounts for local development.

Phase 1 stub: creates two tenants (Westside Home Health, Sunset Hospice)
and one admin user per tenant. Phase 2+ expands this to clinicians,
patients, and 90 days of historical visits.

Invocation:
    python manage.py seed_demo --idempotent   # skip if already seeded
    python manage.py seed_demo --force        # wipe and reseed
"""

import os

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Role, User
from tenancy.models import Tenant

DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "demo1234")

TENANTS: list[dict[str, str]] = [
    {"name": "Westside Home Health", "timezone": "America/Los_Angeles"},
    {"name": "Sunset Hospice", "timezone": "America/Los_Angeles"},
]

ADMINS: list[dict[str, str]] = [
    {"tenant": "Westside Home Health", "email": "admin@westside.demo"},
    {"tenant": "Sunset Hospice", "email": "admin@sunset.demo"},
]


class Command(BaseCommand):
    help = "Seed demo tenants and default accounts. Phase 1 stub."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--idempotent",
            action="store_true",
            help="Skip if demo data already present.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Wipe all tenants and users before seeding.",
        )

    def handle(self, *args, **opts) -> None:
        if opts["force"]:
            User.objects.all().delete()
            Tenant.objects.all().delete()
        elif opts["idempotent"] and Tenant.objects.count() >= len(TENANTS):
            self.stdout.write("Already seeded — skipping (use --force to reseed).")
            return

        with transaction.atomic():
            tenants_by_name: dict[str, Tenant] = {}
            for t in TENANTS:
                tenant, _ = Tenant.objects.update_or_create(
                    name=t["name"],
                    defaults={"timezone": t["timezone"]},
                )
                tenants_by_name[t["name"]] = tenant

            for admin in ADMINS:
                tenant = tenants_by_name[admin["tenant"]]
                if User.objects.filter(email=admin["email"], tenant=tenant).exists():
                    continue
                User.objects.create_user(
                    email=admin["email"],
                    password=DEMO_PASSWORD,
                    tenant=tenant,
                    role=Role.ADMIN,
                )

        self.stdout.write(self.style.SUCCESS("Seed complete."))
