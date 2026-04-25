"""Seed demo tenants, clinicians, patients, and visits for local development.

Phase 3 scale (per tenant):
    - 25 clinicians with home coords in the LA basin
    - 300 patients with addresses + required_skill
    - 80 SCHEDULED visits for "today"
    - 90 days × 20 COMPLETED visits per day of historical data

Everything runs under a deterministic seed so `--force` produces the same
fixture twice. Idempotent re-runs without `--force` short-circuit on count.

Invocation:
    python manage.py seed_demo --idempotent   # skip if already seeded
    python manage.py seed_demo --force        # wipe and reseed
"""

from __future__ import annotations

import os
import random
from datetime import UTC, datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import Role, User
from clinicians.models import Clinician, Credential
from patients.models import Patient
from tenancy.models import Tenant
from visits.models import Visit, VisitStatus

DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "demo1234")

TENANTS: list[dict[str, str]] = [
    {"name": "Westside Home Health", "timezone": "America/Los_Angeles", "slug": "westside"},
    {"name": "Sunset Hospice", "timezone": "America/Los_Angeles", "slug": "sunset"},
]

ADMINS: list[dict[str, str]] = [
    {"tenant": "Westside Home Health", "email": "admin@westside.demo"},
    {"tenant": "Sunset Hospice", "email": "admin@sunset.demo"},
]

CLINICIANS_PER_TENANT = 25
PATIENTS_PER_TENANT = 300
TODAY_VISITS_PER_TENANT = 80
HISTORY_DAYS = 90
HISTORY_VISITS_PER_DAY = 20
HISTORY_PER_TENANT = HISTORY_DAYS * HISTORY_VISITS_PER_DAY

_SEED_BASE = 20260424
_CREDENTIALS: tuple[str, ...] = (
    Credential.RN,
    Credential.LVN,
    Credential.MA,
    Credential.PHLEBOTOMIST,
)
_SKILLS: tuple[str, ...] = _CREDENTIALS


def _rng(tenant_name: str) -> random.Random:
    return random.Random(f"{_SEED_BASE}-{tenant_name}")


def _seed_clinicians(tenant: Tenant, slug: str, rng: random.Random) -> list[Clinician]:
    existing = list(Clinician.objects.filter(tenant=tenant).order_by("id"))
    if len(existing) >= CLINICIANS_PER_TENANT:
        return existing
    created: list[Clinician] = []
    for i in range(len(existing), CLINICIANS_PER_TENANT):
        u = User(email=f"c{i:02d}@{slug}.demo", tenant=tenant, role=Role.CLINICIAN)
        u.set_unusable_password()
        u.save()
        c = Clinician.objects.create(
            user=u,
            tenant=tenant,
            credential=_CREDENTIALS[i % len(_CREDENTIALS)],
            home_lat=rng.uniform(33.90, 34.20),
            home_lon=rng.uniform(-118.50, -118.00),
        )
        created.append(c)
    return existing + created


def _seed_patients(tenant: Tenant, rng: random.Random) -> list[Patient]:
    existing = Patient.objects.filter(tenant=tenant).count()
    if existing >= PATIENTS_PER_TENANT:
        return list(Patient.objects.filter(tenant=tenant).order_by("id"))
    batch: list[Patient] = []
    for i in range(existing, PATIENTS_PER_TENANT):
        batch.append(
            Patient(
                tenant=tenant,
                name=f"Patient {i:04d}",
                phone=f"+1555{i:07d}",
                address=f"{i} Main St, Los Angeles, CA",
                lat=rng.uniform(33.90, 34.20),
                lon=rng.uniform(-118.50, -118.00),
                required_skill=_SKILLS[i % len(_SKILLS)],
            )
        )
    Patient.objects.bulk_create(batch, batch_size=200)
    return list(Patient.objects.filter(tenant=tenant).order_by("id"))


def _seed_today_visits(tenant: Tenant, patients: list[Patient], rng: random.Random) -> None:
    today = timezone.localdate()
    today_existing = Visit.objects.filter(tenant=tenant, window_start__date=today).count()
    to_create = TODAY_VISITS_PER_TENANT - today_existing
    if to_create <= 0:
        return
    batch: list[Visit] = []
    for _ in range(to_create):
        p = rng.choice(patients)
        hour = rng.randint(8, 15)
        start = datetime.combine(today, time(hour=hour), tzinfo=UTC)
        batch.append(
            Visit(
                tenant=tenant,
                patient=p,
                window_start=start,
                window_end=start + timedelta(hours=2),
                required_skill=p.required_skill,
                status=VisitStatus.SCHEDULED,
            )
        )
    Visit.objects.bulk_create(batch, batch_size=200)


def _seed_history_visits(
    tenant: Tenant,
    clinicians: list[Clinician],
    patients: list[Patient],
    rng: random.Random,
) -> None:
    history_existing = Visit.objects.filter(tenant=tenant, status=VisitStatus.COMPLETED).count()
    if history_existing >= HISTORY_PER_TENANT:
        return
    today = timezone.localdate()
    batch: list[Visit] = []
    for d in range(1, HISTORY_DAYS + 1):
        day = today - timedelta(days=d)
        for _ in range(HISTORY_VISITS_PER_DAY):
            p = rng.choice(patients)
            c = rng.choice(clinicians)
            hour = rng.randint(8, 15)
            start = datetime.combine(day, time(hour=hour), tzinfo=UTC)
            on_time = rng.random() < 0.90
            delay_min = 0 if on_time else rng.randint(20, 60)
            checkin = start + timedelta(minutes=delay_min)
            checkout = checkin + timedelta(minutes=30)
            batch.append(
                Visit(
                    tenant=tenant,
                    patient=p,
                    clinician=c,
                    window_start=start,
                    window_end=start + timedelta(hours=2),
                    required_skill=p.required_skill,
                    status=VisitStatus.COMPLETED,
                    check_in_at=checkin,
                    check_out_at=checkout,
                )
            )
    Visit.objects.bulk_create(batch, batch_size=500)


class Command(BaseCommand):
    help = "Seed demo tenants, clinicians, patients, and visits."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--idempotent",
            action="store_true",
            help="Skip if demo data already present.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Wipe all tenants (cascades to everything) before seeding.",
        )
        parser.add_argument(
            "--enable-clinician-login",
            action="store_true",
            help="Set DEMO_PASSWORD on the first clinician account per tenant "
            "so the Phase 6 clinician view can log in. Off by default.",
        )

    def handle(self, *args, **opts) -> None:
        if opts["force"]:
            Tenant.objects.all().delete()
        elif opts["idempotent"] and self._already_seeded():
            self.stdout.write("Already seeded — skipping (use --force to reseed).")
            if opts.get("enable_clinician_login"):
                self._enable_clinician_login()
                self.stdout.write(self.style.SUCCESS("Clinician login enabled."))
            return

        with transaction.atomic():
            tenants_by_name = self._ensure_tenants_and_admins()
            for cfg in TENANTS:
                tenant = tenants_by_name[cfg["name"]]
                rng = _rng(cfg["name"])
                clinicians = _seed_clinicians(tenant, cfg["slug"], rng)
                patients = _seed_patients(tenant, rng)
                _seed_today_visits(tenant, patients, rng)
                _seed_history_visits(tenant, clinicians, patients, rng)

        if opts.get("enable_clinician_login"):
            self._enable_clinician_login()

        self.stdout.write(self.style.SUCCESS("Seed complete."))

    def _enable_clinician_login(self) -> None:
        """Set a usable password on c00@<slug>.demo per tenant."""
        for cfg in TENANTS:
            tenant = Tenant.objects.filter(name=cfg["name"]).first()
            if tenant is None:
                continue
            email = f"c00@{cfg['slug']}.demo"
            user = User.objects.filter(email=email, tenant=tenant).first()
            if user is None:
                continue
            user.set_password(DEMO_PASSWORD)
            user.save(update_fields=["password"])

    def _already_seeded(self) -> bool:
        if Tenant.objects.count() < len(TENANTS):
            return False
        for cfg in TENANTS:
            tenant = Tenant.objects.filter(name=cfg["name"]).first()
            if tenant is None:
                return False
            if Clinician.objects.filter(tenant=tenant).count() < CLINICIANS_PER_TENANT:
                return False
            if Patient.objects.filter(tenant=tenant).count() < PATIENTS_PER_TENANT:
                return False
        return True

    def _ensure_tenants_and_admins(self) -> dict[str, Tenant]:
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
        return tenants_by_name
