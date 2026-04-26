"""Celery tasks for the scheduling app.

optimize_day: the big one — take a (tenant, date), solve the VRP, persist
per-clinician RoutePlan rows, and stamp each affected visit with its
assigned clinician + order. Idempotent: re-running for the same date
replaces prior plans via update_or_create.
"""

from __future__ import annotations

from datetime import date as _date

from celery import shared_task
from django.db import transaction

from core.events import publish, schedule_optimized, visit_reassigned
from routing.models import RoutePlan
from scheduling.adapter import build_problem
from scheduling.ranker import Ranker
from scheduling.rerank import build_rerank_costs
from scheduling.vrp import solve
from tenancy.models import Tenant
from visits.models import Visit, VisitStatus

_SOLVER_VERSION = "phase3-t7"

# Cached at module load. The Ranker reads its pickle eagerly on init and
# falls through to a constant 0.5 if the artifact is absent. The cache
# matters because Celery worker processes are long-lived; we don't want
# to re-pickle.load on every optimize_day call.
_RANKER: Ranker | None = None


def _get_ranker() -> Ranker:
    global _RANKER
    if _RANKER is None:
        _RANKER = Ranker()
    return _RANKER


@shared_task(name="scheduling.ping")
def ping() -> str:
    """Round-trip sanity task. Returns 'pong'."""
    return "pong"


@shared_task(name="scheduling.optimize_day")
def optimize_day(tenant_id: int, iso_date: str, time_budget_s: int = 10) -> dict:
    tenant = Tenant.objects.get(id=tenant_id)
    target_date = _date.fromisoformat(iso_date)
    problem = build_problem(tenant, target_date)

    # Wire the re-ranker into the solver objective when a trained
    # artifact is present. Without one, leave problem.rerank_costs as
    # None so the solver uses its legacy single-callback arc cost.
    ranker = _get_ranker()
    if ranker.is_loaded:
        problem.rerank_costs = build_rerank_costs(problem, ranker, tz_name=tenant.timezone or "UTC")

    solution = solve(problem, time_budget_s=time_budget_s)

    with transaction.atomic():
        for route in solution.routes:
            if not route.visit_ids:
                continue
            RoutePlan.objects.update_or_create(
                tenant=tenant,
                clinician_id=route.clinician_id,
                date=target_date,
                defaults={
                    "visits_ordered": list(route.visit_ids),
                    "solver_metadata": {
                        "travel_seconds": route.travel_seconds,
                        "solver_version": _SOLVER_VERSION,
                    },
                },
            )
            for seq, visit_id in enumerate(route.visit_ids):
                # Stamp clinician + ordering on every assigned visit; promote
                # SCHEDULED rows to ASSIGNED so the clinician's check-in path
                # accepts them. Visits already further along (en_route /
                # on_site / completed) keep their existing status.
                Visit.objects.filter(
                    id=visit_id, tenant=tenant, status=VisitStatus.SCHEDULED
                ).update(
                    clinician_id=route.clinician_id,
                    ordering_seq=seq,
                    status=VisitStatus.ASSIGNED,
                )
                Visit.objects.filter(id=visit_id, tenant=tenant).exclude(
                    status=VisitStatus.SCHEDULED
                ).update(
                    clinician_id=route.clinician_id,
                    ordering_seq=seq,
                )

    summary = {
        "routes": sum(1 for r in solution.routes if r.visit_ids),
        "unassigned": len(solution.unassigned_visit_ids),
        "total_travel_s": solution.total_travel_s,
    }
    publish(tenant.id, schedule_optimized(tenant.id, target_date.isoformat(), summary))
    for route in solution.routes:
        for visit_id in route.visit_ids:
            publish(
                tenant.id,
                visit_reassigned(
                    Visit(id=visit_id, tenant_id=tenant.id, clinician_id=route.clinician_id)
                ),
            )
    return summary
