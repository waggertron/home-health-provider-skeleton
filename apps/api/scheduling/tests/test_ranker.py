import pickle
from pathlib import Path

import numpy as np
import pytest
from sklearn.ensemble import GradientBoostingRegressor

from scheduling.ranker import Ranker, extract_features


def test_extract_features_returns_five_floats():
    features = extract_features(
        historical_on_time_rate=0.9,
        visits_to_patient_count=3,
        credential_rank_gap=1,
        hour_of_day=10,
        day_of_week=2,
    )
    assert isinstance(features, list)
    assert len(features) == 5
    assert all(isinstance(f, float) for f in features)


def test_ranker_returns_half_when_no_model_on_disk(tmp_path: Path):
    ranker = Ranker(model_path=tmp_path / "does_not_exist.pkl")
    features = extract_features(
        historical_on_time_rate=0.9,
        visits_to_patient_count=3,
        credential_rank_gap=1,
        hour_of_day=10,
        day_of_week=2,
    )
    assert ranker.score(features) == pytest.approx(0.5)


def test_ranker_deterministic_when_model_loaded(tmp_path: Path):
    # Train a tiny deterministic model and pickle it.
    rng = np.random.default_rng(42)
    X = rng.random((50, 5))
    y = X[:, 0] * 0.7 + X[:, 2] * 0.2  # on-time rate + credential gap weight
    model = GradientBoostingRegressor(random_state=0).fit(X, y)
    path = tmp_path / "ranker.pkl"
    with path.open("wb") as f:
        pickle.dump(model, f)

    ranker = Ranker(model_path=path)
    features = extract_features(
        historical_on_time_rate=0.9,
        visits_to_patient_count=3,
        credential_rank_gap=1,
        hour_of_day=10,
        day_of_week=2,
    )
    first = ranker.score(features)
    second = ranker.score(features)
    assert first == second
    assert first != 0.5  # actually ran the model
