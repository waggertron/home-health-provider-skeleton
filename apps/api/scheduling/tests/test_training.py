from io import StringIO
from pathlib import Path

from django.core.management import call_command

from scheduling.ranker import Ranker
from scheduling.training import generate_synthetic_history, train_ranker


def test_generate_synthetic_history_is_deterministic_under_seed():
    a = generate_synthetic_history(days=10, seed=42)
    b = generate_synthetic_history(days=10, seed=42)
    assert a == b
    assert len(a) == 10 * 20  # 20 rows/day


def test_generate_synthetic_history_varies_with_seed():
    a = generate_synthetic_history(days=5, seed=1)
    b = generate_synthetic_history(days=5, seed=2)
    assert a != b


def test_train_ranker_writes_pickle_and_predicts_non_constant(tmp_path: Path):
    history = generate_synthetic_history(days=30, seed=1)
    path = tmp_path / "ranker.pkl"
    train_ranker(history, model_path=path)
    assert path.exists()

    ranker = Ranker(model_path=path)
    high_on_time = [0.95, 5.0, 2.0, 10.0, 1.0]
    low_on_time = [0.60, 0.0, 0.0, 17.0, 4.0]
    assert ranker.score(high_on_time) != ranker.score(low_on_time)


def test_train_ranker_management_command_writes_artifact(tmp_path: Path, monkeypatch):
    artifact = tmp_path / "artifacts" / "ranker.pkl"
    monkeypatch.setattr("scheduling.training._ARTIFACT_PATH", artifact)
    out = StringIO()
    call_command("train_ranker", "--days", "5", "--seed", "7", stdout=out)
    assert artifact.exists()
    assert "Wrote" in out.getvalue()
