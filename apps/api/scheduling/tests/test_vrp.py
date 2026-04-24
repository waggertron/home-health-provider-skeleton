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


def test_solve_three_visits_one_clinician_respects_time_window_ordering():
    # One RN clinician, three RN visits on a line. Time windows force order 1→2→3.
    clinician = ClinicianNode(id=100, home_lat=34.0, home_lon=-118.0, credential="RN")
    # Tight windows so the only feasible order is 1→2→3. Travel ≈100s per step
    # with 34.0 depot spacing; service = 1800s per visit.
    visits = [
        VisitNode(
            id=1, lat=34.01, lon=-118.0, window_start_s=0, window_end_s=3600, required_skill="RN"
        ),
        VisitNode(
            id=2, lat=34.02, lon=-118.0, window_start_s=1800, window_end_s=5400, required_skill="RN"
        ),
        VisitNode(
            id=3, lat=34.03, lon=-118.0, window_start_s=3600, window_end_s=7200, required_skill="RN"
        ),
    ]
    coords = [(clinician.home_lat, clinician.home_lon)] + [(v.lat, v.lon) for v in visits]
    problem = Problem(
        tenant_id=1,
        date=date(2026, 4, 24),
        clinicians=[clinician],
        visits=visits,
        distance_matrix=_matrix(coords),
        allowed_vehicles=[[0], [0], [0]],
    )
    solution = solve(problem, time_budget_s=2)
    assert len(solution.routes) == 1
    assert solution.routes[0].clinician_id == 100
    assert solution.routes[0].visit_ids == [1, 2, 3]
    assert solution.unassigned_visit_ids == []


def test_solve_assigns_lvn_visit_to_rn_clinician_not_ma():
    # RN and MA clinicians; one LVN-required visit. MA cannot serve LVN (rank 1 < rank 2).
    rn = ClinicianNode(id=10, home_lat=34.0, home_lon=-118.0, credential="RN")
    ma = ClinicianNode(id=20, home_lat=34.1, home_lon=-118.0, credential="MA")
    lvn_visit = VisitNode(
        id=42,
        lat=34.05,
        lon=-118.0,
        window_start_s=0,
        window_end_s=28800,
        required_skill="LVN",
    )
    coords = [
        (rn.home_lat, rn.home_lon),
        (ma.home_lat, ma.home_lon),
        (lvn_visit.lat, lvn_visit.lon),
    ]
    # Only the RN clinician (vehicle index 0) is allowed.
    problem = Problem(
        tenant_id=1,
        date=date(2026, 4, 24),
        clinicians=[rn, ma],
        visits=[lvn_visit],
        distance_matrix=_matrix(coords),
        allowed_vehicles=[[0]],
    )
    solution = solve(problem, time_budget_s=2)
    assert solution.unassigned_visit_ids == []
    by_clinician = {r.clinician_id: r.visit_ids for r in solution.routes}
    assert 42 in by_clinician[10]
    assert 42 not in by_clinician.get(20, [])
