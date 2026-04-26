"""Per-vehicle rerank-bias tests for the VRP objective.

When `Problem.rerank_costs` is set, the solver must use per-vehicle arc
cost evaluators that include the rerank bias for arcs ending at a
visit. With no rerank costs (None), behavior must be byte-identical to
the pre-rerank solver — back-compat is part of the contract.
"""

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


def _two_rn_one_visit_problem() -> Problem:
    """Two equally-credentialed RN clinicians equidistant from one visit.

    Without a tiebreaker, OR-Tools is free to pick either vehicle; we'll
    use rerank_costs to bias the solve.
    """
    rn_a = ClinicianNode(id=1, home_lat=34.00, home_lon=-118.10, credential="RN")
    rn_b = ClinicianNode(id=2, home_lat=34.00, home_lon=-117.90, credential="RN")
    visit = VisitNode(
        id=99,
        lat=34.00,
        lon=-118.00,
        window_start_s=0,
        window_end_s=28800,
        required_skill="RN",
    )
    coords = [
        (rn_a.home_lat, rn_a.home_lon),
        (rn_b.home_lat, rn_b.home_lon),
        (visit.lat, visit.lon),
    ]
    return Problem(
        tenant_id=1,
        date=date(2026, 4, 24),
        clinicians=[rn_a, rn_b],
        visits=[visit],
        distance_matrix=_matrix(coords),
        allowed_vehicles=[[0, 1]],
    )


def test_rerank_costs_strongly_bias_assignment_to_preferred_vehicle():
    # Heavy bonus for vehicle index 1 (clinician id 2) when serving visit 0.
    # rerank_costs[v_idx][c_idx] = subtractive cost (positive = bonus).
    problem = _two_rn_one_visit_problem()
    problem.rerank_costs = [[0, 100_000]]  # 100k second bonus for clinician 2

    solution = solve(problem, time_budget_s=2)
    assigned = {r.clinician_id: r.visit_ids for r in solution.routes}
    assert assigned[2] == [99], f"expected clinician 2 to win, got {assigned}"
    assert assigned[1] == []


def test_rerank_costs_inverted_bias_picks_other_vehicle():
    # Same problem, opposite bias.
    problem = _two_rn_one_visit_problem()
    problem.rerank_costs = [[100_000, 0]]

    solution = solve(problem, time_budget_s=2)
    assigned = {r.clinician_id: r.visit_ids for r in solution.routes}
    assert assigned[1] == [99], f"expected clinician 1 to win, got {assigned}"
    assert assigned[2] == []


def test_no_rerank_costs_preserves_legacy_behavior():
    # rerank_costs=None should not change anything — the existing test
    # suite covers the no-rerank path; this is a smoke check that None
    # is a no-op (problem still solves, visit still assigned).
    problem = _two_rn_one_visit_problem()
    assert problem.rerank_costs is None  # default

    solution = solve(problem, time_budget_s=2)
    assigned_ids = [v for r in solution.routes for v in r.visit_ids]
    assert assigned_ids == [99]
    assert solution.unassigned_visit_ids == []
