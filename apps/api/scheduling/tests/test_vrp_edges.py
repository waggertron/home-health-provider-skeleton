"""Edge cases for the OR-Tools VRP solver wrapper."""

from datetime import date

from scheduling.adapter import ClinicianNode, Problem, VisitNode
from scheduling.distance import haversine_km, travel_seconds
from scheduling.vrp import solve


def _matrix(coords: list[tuple[float, float]]) -> list[list[int]]:
    n = len(coords)
    m = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            km = haversine_km(coords[i][0], coords[i][1], coords[j][0], coords[j][1])
            t = travel_seconds(km)
            m[i][j] = t
            m[j][i] = t
    return m


def _empty_problem(tenant_id: int = 1) -> Problem:
    return Problem(
        tenant_id=tenant_id,
        date=date(2026, 4, 24),
        clinicians=[],
        visits=[],
        distance_matrix=[],
        allowed_vehicles=[],
    )


def test_solve_empty_problem_returns_empty_solution():
    sol = solve(_empty_problem(), time_budget_s=1)
    assert sol.routes == []
    assert sol.total_travel_s == 0
    assert sol.unassigned_visit_ids == []


def test_solve_no_visits_returns_empty_routes_per_clinician():
    c = ClinicianNode(id=1, home_lat=34.0, home_lon=-118.0, credential="RN")
    problem = Problem(
        tenant_id=1,
        date=date(2026, 4, 24),
        clinicians=[c],
        visits=[],
        distance_matrix=[[0]],
        allowed_vehicles=[],
    )
    sol = solve(problem, time_budget_s=1)
    assert len(sol.routes) == 1
    assert sol.routes[0].clinician_id == 1
    assert sol.routes[0].visit_ids == []


def test_solve_drops_visit_when_no_credentialed_clinician_available():
    # MA clinician only; visit requires RN → infeasible → must drop.
    ma = ClinicianNode(id=20, home_lat=34.0, home_lon=-118.0, credential="MA")
    visit = VisitNode(
        id=42,
        lat=34.01,
        lon=-118.0,
        window_start_s=0,
        window_end_s=28800,
        required_skill="RN",
    )
    coords = [(ma.home_lat, ma.home_lon), (visit.lat, visit.lon)]
    problem = Problem(
        tenant_id=1,
        date=date(2026, 4, 24),
        clinicians=[ma],
        visits=[visit],
        distance_matrix=_matrix(coords),
        allowed_vehicles=[[]],  # no vehicle can serve
    )
    sol = solve(problem, time_budget_s=1)
    assert sol.unassigned_visit_ids == [42]
    assert all(v != 42 for r in sol.routes for v in r.visit_ids)
