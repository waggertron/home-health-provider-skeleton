"""Build a Problem dataclass the VRP solver consumes.

Pulls one tenant's open visits for a given date plus all active clinicians,
builds a travel-time distance matrix, and records which vehicles are
credentialed to serve each visit. The solver layer (scheduling.vrp) consumes
this structure directly — no Django ORM objects cross the adapter boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from clinicians.models import Clinician
from scheduling.distance import haversine_km, travel_seconds
from tenancy.models import Tenant
from visits.models import Visit, VisitStatus

# Credential hierarchy: higher rank can serve any lower-or-equal skill.
# Phlebotomist is a standalone skill — matched exactly, not by hierarchy.
_CRED_RANK = {"MA": 1, "LVN": 2, "RN": 3}

_OPEN_STATUSES = (VisitStatus.SCHEDULED, VisitStatus.ASSIGNED)


def _can_serve(clinician_credential: str, required_skill: str) -> bool:
    if clinician_credential == "phlebotomist" or required_skill == "phlebotomist":
        return clinician_credential == required_skill
    return _CRED_RANK.get(clinician_credential, 0) >= _CRED_RANK.get(required_skill, 0)


@dataclass(frozen=True)
class ClinicianNode:
    id: int
    home_lat: float
    home_lon: float
    credential: str


@dataclass(frozen=True)
class VisitNode:
    id: int
    lat: float
    lon: float
    window_start_s: int
    window_end_s: int
    required_skill: str
    service_time_s: int = 1800  # 30 min default; configurable later.


@dataclass
class Problem:
    tenant_id: int
    date: date
    clinicians: list[ClinicianNode]
    visits: list[VisitNode]
    distance_matrix: list[list[int]]
    allowed_vehicles: list[list[int]]
    # Optional per-vehicle rerank cost adjustment for arcs ending at a
    # visit. Shape: [v_idx][c_idx]; integer "seconds saved" (positive
    # values bias the solver toward that pairing). When None, the solver
    # uses a single global arc-cost evaluator (legacy path).
    rerank_costs: list[list[int]] | None = None


def build_problem(tenant: Tenant, target_date: date) -> Problem:
    tzinfo = ZoneInfo(tenant.timezone or "UTC")
    day_start = datetime.combine(target_date, time.min, tzinfo=tzinfo)
    day_end = day_start + timedelta(days=1)

    clinicians_qs = Clinician.objects.filter(tenant=tenant).order_by("id")
    visits_qs = (
        Visit.objects.filter(
            tenant=tenant,
            window_start__gte=day_start,
            window_start__lt=day_end,
            status__in=_OPEN_STATUSES,
        )
        .select_related("patient")
        .order_by("window_start", "id")
    )

    clinicians = [
        ClinicianNode(
            id=c.id,
            home_lat=c.home_lat,
            home_lon=c.home_lon,
            credential=c.credential,
        )
        for c in clinicians_qs
    ]
    visits = [
        VisitNode(
            id=v.id,
            lat=v.patient.lat,
            lon=v.patient.lon,
            window_start_s=int((v.window_start - day_start).total_seconds()),
            window_end_s=int((v.window_end - day_start).total_seconds()),
            required_skill=v.required_skill,
        )
        for v in visits_qs
    ]

    coords: list[tuple[float, float]] = [(c.home_lat, c.home_lon) for c in clinicians]
    coords.extend((v.lat, v.lon) for v in visits)
    n = len(coords)
    matrix = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            km = haversine_km(coords[i][0], coords[i][1], coords[j][0], coords[j][1])
            t = travel_seconds(km)
            matrix[i][j] = t
            matrix[j][i] = t

    allowed_vehicles = [
        [idx for idx, c in enumerate(clinicians) if _can_serve(c.credential, v.required_skill)]
        for v in visits
    ]

    return Problem(
        tenant_id=tenant.id,
        date=target_date,
        clinicians=clinicians,
        visits=visits,
        distance_matrix=matrix,
        allowed_vehicles=allowed_vehicles,
    )
