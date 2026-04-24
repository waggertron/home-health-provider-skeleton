"""Synthetic training data generator + trainer for the re-ranker.

Produces a deterministic history of (visit, clinician, on_time) rows with no
DB dependency, then fits a GradientBoostingRegressor against the
extract_features feature vector. The trained model is pickled to
scheduling/artifacts/ranker.pkl (gitignored).
"""

from __future__ import annotations

import pickle
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from scheduling.ranker import extract_features

_ARTIFACT_PATH = Path(__file__).resolve().parent / "artifacts" / "ranker.pkl"

# Credential hierarchy kept local to avoid re-importing adapter for a trivial map.
_CRED_RANK = {"MA": 1, "LVN": 2, "RN": 3}
_CREDENTIALS: tuple[str, ...] = ("RN", "LVN", "MA")
_ROWS_PER_DAY = 20


@dataclass(frozen=True)
class HistoryRow:
    clinician_credential: str
    required_skill: str
    scheduled_at: datetime
    visits_to_patient_count: int
    historical_on_time_rate: float
    on_time: bool


def generate_synthetic_history(days: int = 90, seed: int = 0) -> list[HistoryRow]:
    """Deterministic training set — ~20 rows/day under a fixed seed."""
    rng = random.Random(seed)
    start = datetime(2026, 1, 1, tzinfo=UTC)
    rows: list[HistoryRow] = []
    for d in range(days):
        day = start + timedelta(days=d)
        for _ in range(_ROWS_PER_DAY):
            cred = rng.choice(_CREDENTIALS)
            valid_skills = [s for s in _CREDENTIALS if _CRED_RANK[s] <= _CRED_RANK[cred]]
            skill = rng.choice(valid_skills)
            hour = rng.randint(8, 17)
            scheduled = day.replace(hour=hour)
            visits_to_patient = rng.randint(0, 5)
            baseline = rng.uniform(0.60, 0.98)
            # Late-day rush pulls on-time probability down.
            rush_penalty = 0.15 if hour >= 16 else 0.0
            p_on_time = max(0.05, baseline - rush_penalty)
            on_time = rng.random() < p_on_time
            rows.append(
                HistoryRow(
                    clinician_credential=cred,
                    required_skill=skill,
                    scheduled_at=scheduled,
                    visits_to_patient_count=visits_to_patient,
                    historical_on_time_rate=baseline,
                    on_time=on_time,
                )
            )
    return rows


def _row_to_features(row: HistoryRow) -> list[float]:
    return extract_features(
        historical_on_time_rate=row.historical_on_time_rate,
        visits_to_patient_count=row.visits_to_patient_count,
        credential_rank_gap=_CRED_RANK[row.clinician_credential] - _CRED_RANK[row.required_skill],
        hour_of_day=row.scheduled_at.hour,
        day_of_week=row.scheduled_at.weekday(),
    )


def train_ranker(history: list[HistoryRow], model_path: Path | None = None) -> Path:
    """Fit the regressor and pickle it. Returns the artifact path."""
    from sklearn.ensemble import GradientBoostingRegressor

    target = model_path or _ARTIFACT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)

    x_rows = [_row_to_features(r) for r in history]
    y_rows = [1.0 if r.on_time else 0.0 for r in history]
    model = GradientBoostingRegressor(random_state=0).fit(x_rows, y_rows)

    with target.open("wb") as f:
        pickle.dump(model, f)
    return target
