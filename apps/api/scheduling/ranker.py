"""ML re-ranker: scores clinician-visit pairings for the VRP objective.

Loads a pickled GradientBoostingRegressor from disk. If the artifact is
missing, every pair scores a constant 0.5 so the solver degenerates to
pure travel-time minimization. Training lives in scheduling.training.
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

import numpy as np

_DEFAULT_MODEL_PATH = Path(__file__).resolve().parent / "artifacts" / "ranker.pkl"

FEATURE_ORDER = (
    "historical_on_time_rate",
    "visits_to_patient_count",
    "credential_rank_gap",
    "hour_of_day",
    "day_of_week",
)


def extract_features(
    *,
    historical_on_time_rate: float,
    visits_to_patient_count: int,
    credential_rank_gap: int,
    hour_of_day: int,
    day_of_week: int,
) -> list[float]:
    return [
        float(historical_on_time_rate),
        float(visits_to_patient_count),
        float(credential_rank_gap),
        float(hour_of_day),
        float(day_of_week),
    ]


class Ranker:
    """Wraps a pickled sklearn regressor with a graceful no-model fallback."""

    def __init__(self, model_path: Path | None = None) -> None:
        self._path = model_path or _DEFAULT_MODEL_PATH
        self._model: Any = None
        if self._path.exists():
            with self._path.open("rb") as f:
                self._model = pickle.load(f)  # noqa: S301 — artifact we produce

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def score(self, features: list[float]) -> float:
        if self._model is None:
            return 0.5
        prediction = self._model.predict(np.array([features], dtype=float))
        return float(prediction[0])
