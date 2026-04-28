"""Tests for the Metabase bootstrap helpers (post-v1 #4).

The pure payload builders get straight unit tests. The orchestrator is
exercised against a mocked Session so the test suite has no Metabase
dependency.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from reporting.metabase_bootstrap import (
    BootstrapConfig,
    bootstrap,
    build_card_payload,
    build_database_payload,
    build_setup_payload,
    fetch_setup_token,
    wait_for_metabase,
)


def _ok(json_body: dict[str, Any] | None = None, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = json_body or {}
    resp.raise_for_status = MagicMock()
    return resp


def test_build_database_payload_uses_metabase_ro_credentials():
    cfg = BootstrapConfig()
    payload = build_database_payload(cfg)
    assert payload["engine"] == "postgres"
    assert payload["details"]["user"] == "metabase_ro"
    assert payload["details"]["dbname"] == "hhps"
    assert payload["details"]["host"] == "db-postgres"
    assert payload["details"]["port"] == 5432
    # The schema filter restricts Metabase visibility to the reporting schema.
    assert payload["details"]["schema-filters-type"] == "inclusion"
    assert payload["details"]["schema-filters-patterns"] == "reporting"


def test_build_card_payload_carries_database_id_and_sql():
    cfg = BootstrapConfig()
    payload = build_card_payload(database_id=42, cfg=cfg)
    assert payload["dataset_query"]["database"] == 42
    assert payload["dataset_query"]["type"] == "native"
    sql = payload["dataset_query"]["native"]["query"]
    assert "reporting.daily_agency_stats" in sql
    assert "ORDER BY date DESC" in sql


def test_build_setup_payload_composes_user_prefs_and_database():
    cfg = BootstrapConfig()
    payload = build_setup_payload("setup-tok", cfg)
    assert payload["token"] == "setup-tok"
    assert payload["user"]["email"] == cfg.admin_email
    assert payload["prefs"]["site_name"] == cfg.site_name
    assert payload["database"]["details"]["user"] == "metabase_ro"


def test_wait_for_metabase_returns_true_on_first_200():
    session = MagicMock()
    session.get.return_value = _ok({})
    assert wait_for_metabase(session, "http://x", timeout_s=5) is True


def test_wait_for_metabase_returns_false_when_health_never_200(monkeypatch):
    session = MagicMock()
    session.get.return_value = _ok({}, status=503)
    # Collapse sleep so the test stays fast.
    import reporting.metabase_bootstrap as mod

    monkeypatch.setattr(mod.time, "sleep", lambda *_: None)
    monkeypatch.setattr(mod.time, "monotonic", _bounded_clock(2))
    assert wait_for_metabase(session, "http://x", timeout_s=1) is False


def test_fetch_setup_token_returns_none_when_already_set_up():
    session = MagicMock()
    session.get.return_value = _ok({"setup-token": None})
    assert fetch_setup_token(session, "http://x") is None


def test_bootstrap_happy_path_returns_public_url(monkeypatch):
    session = MagicMock()

    def get(url: str, **_: Any) -> MagicMock:
        if url.endswith("/api/health"):
            return _ok({})
        if url.endswith("/api/session/properties"):
            return _ok({"setup-token": "stk"})
        raise AssertionError(f"unexpected GET {url}")

    posts: dict[str, MagicMock] = {
        "/api/setup": _ok({"id": "sess-1", "database": {"id": 7}}),
        "/api/card": _ok({"id": 11}),
        "/api/dashboard": _ok({"id": 22}),
        "/api/dashboard/22/cards": _ok({}),
        "/api/dashboard/22/public_link": _ok({"uuid": "abc-123"}),
    }

    def post(url: str, **_: Any) -> MagicMock:
        for suffix, resp in posts.items():
            if url.endswith(suffix):
                return resp
        raise AssertionError(f"unexpected POST {url}")

    session.get.side_effect = get
    session.post.side_effect = post
    session.put.return_value = _ok({})

    cfg = BootstrapConfig(base_url="http://mb")
    url = bootstrap(session, cfg)
    assert url == "http://mb/public/dashboard/abc-123"


def test_bootstrap_returns_none_when_already_set_up():
    session = MagicMock()
    session.get.side_effect = lambda url, **_: (
        _ok({}) if url.endswith("/api/health") else _ok({"setup-token": None})
    )
    cfg = BootstrapConfig(base_url="http://mb")
    assert bootstrap(session, cfg) is None
    session.post.assert_not_called()


def _bounded_clock(steps: int):
    """Returns a callable that advances by 10s each call, terminating after
    `steps` invocations to make a polling loop bail out fast."""
    counter = {"n": 0}

    def now() -> float:
        counter["n"] += 1
        return float(counter["n"] * 10)

    return now
