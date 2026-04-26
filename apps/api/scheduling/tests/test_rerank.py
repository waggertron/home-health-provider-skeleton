"""Tests for scheduling.rerank.build_rerank_costs."""

from __future__ import annotations

from datetime import date

from scheduling.adapter import ClinicianNode, Problem, VisitNode
from scheduling.ranker import Ranker
from scheduling.rerank import build_rerank_costs


def _problem() -> Problem:
    rn = ClinicianNode(id=1, home_lat=34.0, home_lon=-118.0, credential="RN")
    ma = ClinicianNode(id=2, home_lat=34.0, home_lon=-118.1, credential="MA")
    visit = VisitNode(
        id=10,
        lat=34.0,
        lon=-118.05,
        window_start_s=8 * 3600,
        window_end_s=12 * 3600,
        required_skill="LVN",
    )
    matrix = [[0, 100, 200], [100, 0, 100], [200, 100, 0]]
    # MA cannot serve LVN; only RN (vehicle 0) is allowed.
    allowed = [[0]]
    return Problem(
        tenant_id=1,
        date=date(2026, 4, 26),
        clinicians=[rn, ma],
        visits=[visit],
        distance_matrix=matrix,
        allowed_vehicles=allowed,
    )


def test_build_rerank_costs_uses_default_score_when_no_artifact(tmp_path):
    # Ranker with a non-existent path → no model loaded → score returns 0.5.
    ranker = Ranker(model_path=tmp_path / "missing.pkl")
    assert not ranker.is_loaded

    problem = _problem()
    costs = build_rerank_costs(problem, ranker, gamma=600.0)

    # Shape: 1 visit × 2 clinicians.
    assert len(costs) == 1
    assert len(costs[0]) == 2
    # Allowed pairing (RN, LVN) gets the default 0.5 * 600 = 300 bonus.
    assert costs[0][0] == 300
    # Disallowed pairing (MA cannot serve LVN) gets 0, regardless of score.
    assert costs[0][1] == 0


def test_build_rerank_costs_zero_for_disallowed_vehicles(tmp_path):
    # Even if every clinician scored perfectly, the credential rule wins.
    ranker = Ranker(model_path=tmp_path / "missing.pkl")
    problem = _problem()
    # Force-disallow vehicle 0 too — we expect everything to be 0.
    problem.allowed_vehicles = [[]]
    costs = build_rerank_costs(problem, ranker, gamma=1000.0)
    assert costs == [[0, 0]]


def test_build_rerank_costs_scales_with_gamma(tmp_path):
    ranker = Ranker(model_path=tmp_path / "missing.pkl")  # constant 0.5
    problem = _problem()
    low = build_rerank_costs(problem, ranker, gamma=100.0)
    high = build_rerank_costs(problem, ranker, gamma=1000.0)
    assert low[0][0] == 50
    assert high[0][0] == 500
