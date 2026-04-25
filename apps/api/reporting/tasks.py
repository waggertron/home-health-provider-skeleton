"""Celery task wrapper for the daily rollup."""

from datetime import date as _date, datetime, timedelta

from celery import shared_task
from django.utils import timezone

from reporting.rollup import rollup_daily


@shared_task(name="reporting.rollup_daily")
def rollup_daily_task(target_date: str | None = None, tenant_id: int | None = None) -> dict:
    """Run rollup_daily for the given ISO date (defaults to yesterday)."""
    if target_date is not None:
        target = _date.fromisoformat(target_date)
    else:
        target = timezone.localdate() - timedelta(days=1)
    summary = rollup_daily(target, tenant_id=tenant_id)
    return {
        "date": target.isoformat(),
        "clinician_rows": summary["clinician_rows"],
        "agency_rows": summary["agency_rows"],
        "ran_at": datetime.now(tz=timezone.get_current_timezone()).isoformat(),
    }
