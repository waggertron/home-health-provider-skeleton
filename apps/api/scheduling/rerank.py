"""Build a rerank cost matrix from a Problem + a Ranker.

Shape: result[v_idx][c_idx] is an integer "seconds saved" bias the VRP
should grant to the (visit, clinician) pairing. The bias is the
re-ranker's score (in [0, 1]) scaled by `gamma`, expressed in seconds
so it composes cleanly with travel time. A higher score means a more
desirable pairing.

Pairings the credential rule already disallows (from
problem.allowed_vehicles) get a 0 bias — the solver isn't going to use
those arcs anyway, so spending features on them is wasted.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from scheduling.adapter import Problem
from scheduling.ranker import Ranker, extract_features

_CRED_RANK = {"MA": 1, "LVN": 2, "RN": 3, "phlebotomist": 0}


def _credential_rank_gap(clinician_credential: str, required_skill: str) -> int:
    return _CRED_RANK.get(clinician_credential, 0) - _CRED_RANK.get(required_skill, 0)


def _hour_and_dow(visit_window_start_s: int, target_date: date, tz_name: str) -> tuple[int, int]:
    tz = ZoneInfo(tz_name or "UTC")
    base = datetime.combine(target_date, time.min, tzinfo=tz)
    when = base + timedelta(seconds=visit_window_start_s)
    return when.hour, when.weekday()


def build_rerank_costs(
    problem: Problem,
    ranker: Ranker,
    gamma: float = 600.0,
    *,
    historical_on_time_rate: float = 0.85,
    visits_to_patient_count: int = 0,
    tz_name: str = "America/Los_Angeles",
) -> list[list[int]]:
    """Return a [v_idx][c_idx] matrix of integer rerank biases (seconds).

    Default `historical_on_time_rate` and `visits_to_patient_count` are
    placeholders for now — feeding the real per-clinician / per-patient
    history through this function is a next step. The structural wiring
    is what this module owns; richer features will plug in via the
    keyword arguments without changing the cost matrix's shape.
    """
    allowed_lookup = [set(allowed) for allowed in problem.allowed_vehicles]
    matrix: list[list[int]] = []

    for v_idx, visit in enumerate(problem.visits):
        hour, dow = _hour_and_dow(visit.window_start_s, problem.date, tz_name)
        row: list[int] = []
        for c_idx, clinician in enumerate(problem.clinicians):
            if c_idx not in allowed_lookup[v_idx]:
                row.append(0)
                continue
            features = extract_features(
                historical_on_time_rate=historical_on_time_rate,
                visits_to_patient_count=visits_to_patient_count,
                credential_rank_gap=_credential_rank_gap(
                    clinician.credential, visit.required_skill
                ),
                hour_of_day=hour,
                day_of_week=dow,
            )
            score = ranker.score(features)
            row.append(int(round(gamma * score)))
        matrix.append(row)

    return matrix
