"""Daily rollup: read yesterday's COMPLETED visits + SmsOutbox rows and
upsert per-clinician + per-tenant stats. Idempotent: re-running for the
same date replaces the existing rows.

Definition of "on-time": check_in_at <= window_start + GRACE.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.db import transaction
from django.utils import timezone

from messaging.models import SmsOutbox
from reporting.models import DailyAgencyStats, DailyClinicianStats
from tenancy.models import Tenant
from visits.models import Visit, VisitStatus

GRACE = timedelta(minutes=15)


@dataclass
class _ClinicianAccum:
    visits_completed: int = 0
    on_time_count: int = 0
    late_count: int = 0
    total_drive_seconds: int = 0
    total_on_site_seconds: int = 0


def _day_bounds(target_date: date, tenant: Tenant) -> tuple[datetime, datetime]:
    tz = ZoneInfo(tenant.timezone or "UTC")
    start = datetime.combine(target_date, time.min, tzinfo=tz)
    return start, start + timedelta(days=1)


@transaction.atomic
def rollup_daily(target_date: date, tenant_id: int | None = None) -> dict:
    """Aggregate visits + SMS for target_date across all tenants (or one)."""
    tenants_qs = Tenant.objects.all()
    if tenant_id is not None:
        tenants_qs = tenants_qs.filter(id=tenant_id)

    summary = {"clinician_rows": 0, "agency_rows": 0}

    for tenant in tenants_qs:
        start, end = _day_bounds(target_date, tenant)

        per_clinician: dict[int, _ClinicianAccum] = defaultdict(_ClinicianAccum)
        agency_completed = 0
        agency_missed = 0
        agency_on_time = 0
        agency_off_time = 0

        completed_qs = Visit.objects.filter(
            tenant=tenant,
            status=VisitStatus.COMPLETED,
            window_start__gte=start,
            window_start__lt=end,
        )
        for v in completed_qs:
            agency_completed += 1
            if v.clinician_id is None:
                continue
            acc = per_clinician[v.clinician_id]
            acc.visits_completed += 1
            on_site_s = 0
            if v.check_in_at and v.check_out_at:
                on_site_s = max(0, int((v.check_out_at - v.check_in_at).total_seconds()))
            acc.total_on_site_seconds += on_site_s
            if v.check_in_at and v.check_in_at <= v.window_start + GRACE:
                acc.on_time_count += 1
                agency_on_time += 1
            else:
                acc.late_count += 1
                agency_off_time += 1

        missed_qs = Visit.objects.filter(
            tenant=tenant,
            status=VisitStatus.MISSED,
            window_start__gte=start,
            window_start__lt=end,
        )
        agency_missed = missed_qs.count()

        sms_total = SmsOutbox.objects.filter(
            tenant=tenant,
            created_at__gte=start,
            created_at__lt=end,
        ).count()
        sms_delivered = SmsOutbox.objects.filter(
            tenant=tenant,
            created_at__gte=start,
            created_at__lt=end,
            status="delivered",
        ).count()

        for clinician_id, acc in per_clinician.items():
            DailyClinicianStats.objects.update_or_create(
                tenant=tenant,
                clinician_id=clinician_id,
                date=target_date,
                defaults={
                    "visits_completed": acc.visits_completed,
                    "on_time_count": acc.on_time_count,
                    "late_count": acc.late_count,
                    "total_drive_seconds": acc.total_drive_seconds,
                    "total_on_site_seconds": acc.total_on_site_seconds,
                },
            )
            summary["clinician_rows"] += 1

        on_time_pct = (
            (agency_on_time / (agency_on_time + agency_off_time))
            if (agency_on_time + agency_off_time)
            else 0.0
        )
        DailyAgencyStats.objects.update_or_create(
            tenant=tenant,
            date=target_date,
            defaults={
                "visits_completed": agency_completed,
                "missed_count": agency_missed,
                "on_time_pct": on_time_pct,
                "sms_sent": sms_total,
                "sms_delivered": sms_delivered,
            },
        )
        summary["agency_rows"] += 1

    return summary


def _today_local() -> date:
    return timezone.localdate()
