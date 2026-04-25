"""python manage.py rollup --date=YYYY-MM-DD [--tenant=N]"""

from datetime import date as _date
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from reporting.rollup import rollup_daily


class Command(BaseCommand):
    help = "Aggregate yesterday's (or a chosen date's) activity into reporting tables."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--date",
            type=str,
            default=None,
            help="Date to roll up (YYYY-MM-DD). Defaults to yesterday in the local TZ.",
        )
        parser.add_argument(
            "--tenant",
            type=int,
            default=None,
            help="Restrict the rollup to a single tenant id. Defaults to all tenants.",
        )

    def handle(self, *args, **opts) -> None:
        if opts["date"]:
            target = _date.fromisoformat(opts["date"])
        else:
            target = timezone.localdate() - timedelta(days=1)
        summary = rollup_daily(target, tenant_id=opts["tenant"])
        self.stdout.write(
            self.style.SUCCESS(
                f"Rollup complete for {target}: "
                f"{summary['clinician_rows']} clinician rows, "
                f"{summary['agency_rows']} agency rows."
            )
        )
