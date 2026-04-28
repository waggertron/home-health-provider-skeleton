"""Idempotent Metabase first-boot provisioner (post-v1 #4).

Hits Metabase's REST API to:
  1. Wait for the /api/health endpoint to return 200.
  2. Pull a setup token from /api/session/properties (only valid before
     the first admin is created).
  3. POST /api/setup to create an admin user + register the platform's
     Postgres DB via the metabase_ro role.
  4. Create a "Daily agency stats" SQL card.
  5. Create an "Agency overview" dashboard containing that card.
  6. Enable public sharing globally and mark the dashboard public.
  7. Print the public dashboard URL to stdout.

Re-runnable: if /api/session/properties no longer offers a setup token
(an admin already exists), the script logs and exits 0. The
provisioning is therefore safe to invoke as a compose one-shot.

Pure-Python building blocks live here so they can be unit-tested
without an actual Metabase running. The orchestrator function
`bootstrap()` composes them via `requests.Session`; tests substitute a
mocked session.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BootstrapConfig:
    base_url: str = "http://localhost:3000"
    admin_email: str = "admin@hhps.demo"
    admin_password: str = "demo1234"
    site_name: str = "HHPS Demo"
    db_name: str = "HHPS Reporting"
    db_host: str = "db-postgres"
    db_port: int = 5432
    db_dbname: str = "hhps"
    db_user: str = "metabase_ro"
    db_password: str = "metabase_ro_demo"
    dashboard_name: str = "Agency overview"
    card_name: str = "Daily agency stats (last 30d)"


# `Session` here is structural — `requests.Session` (production) or a
# MagicMock (tests). mypy's strict signature comparison rejects a
# Protocol against requests.Session, so we use `Any` instead. The real
# constraint is that the object exposes `.get()`, `.post()`, and `.put()`
# with the requests-style signature — a hand-rolled Protocol bought
# nothing here but compile pain.
Session = Any


def build_setup_payload(token: str, cfg: BootstrapConfig) -> dict[str, Any]:
    return {
        "token": token,
        "user": {
            "email": cfg.admin_email,
            "password": cfg.admin_password,
            "first_name": "Demo",
            "last_name": "Admin",
            "site_name": cfg.site_name,
        },
        "prefs": {
            "site_name": cfg.site_name,
            "allow_tracking": False,
        },
        "database": build_database_payload(cfg),
    }


def build_database_payload(cfg: BootstrapConfig) -> dict[str, Any]:
    return {
        "engine": "postgres",
        "name": cfg.db_name,
        "details": {
            "host": cfg.db_host,
            "port": cfg.db_port,
            "dbname": cfg.db_dbname,
            "user": cfg.db_user,
            "password": cfg.db_password,
            "ssl": False,
            "schema-filters-type": "inclusion",
            "schema-filters-patterns": "reporting",
        },
        "is_full_sync": True,
    }


def build_card_payload(database_id: int, cfg: BootstrapConfig) -> dict[str, Any]:
    sql = (
        "SELECT date, visits_completed, missed_count, on_time_pct, "
        "sms_delivered "
        "FROM reporting.daily_agency_stats "
        "ORDER BY date DESC LIMIT 30"
    )
    return {
        "name": cfg.card_name,
        "display": "table",
        "visualization_settings": {},
        "dataset_query": {
            "type": "native",
            "database": database_id,
            "native": {"query": sql},
        },
    }


def build_dashboard_payload(cfg: BootstrapConfig) -> dict[str, Any]:
    return {"name": cfg.dashboard_name, "description": "Daily agency rollup overview."}


def wait_for_metabase(session: Session, base_url: str, timeout_s: int = 120) -> bool:
    """Block until /api/health returns 200 or the timeout elapses."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            r = session.get(f"{base_url}/api/health", timeout=5)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(2)
    return False


def fetch_setup_token(session: Session, base_url: str) -> str | None:
    r = session.get(f"{base_url}/api/session/properties", timeout=10)
    r.raise_for_status()
    body = r.json()
    token = body.get("setup-token")
    return token if isinstance(token, str) and token else None


def post_setup(session: Session, base_url: str, payload: dict[str, Any]) -> tuple[str, int | None]:
    """Returns (session_id, database_id)."""
    r = session.post(f"{base_url}/api/setup", json=payload, timeout=30)
    r.raise_for_status()
    body = r.json()
    session_id = body.get("id") or body.get("session_id") or ""
    db_id = body.get("database", {}).get("id") if isinstance(body.get("database"), dict) else None
    return session_id, db_id


def auth_headers(session_id: str) -> dict[str, str]:
    return {"X-Metabase-Session": session_id}


def create_card(session: Session, base_url: str, session_id: str, payload: dict[str, Any]) -> int:
    r = session.post(
        f"{base_url}/api/card", json=payload, headers=auth_headers(session_id), timeout=30
    )
    r.raise_for_status()
    return int(r.json()["id"])


def create_dashboard(
    session: Session, base_url: str, session_id: str, payload: dict[str, Any]
) -> int:
    r = session.post(
        f"{base_url}/api/dashboard",
        json=payload,
        headers=auth_headers(session_id),
        timeout=30,
    )
    r.raise_for_status()
    return int(r.json()["id"])


def add_card_to_dashboard(
    session: Session, base_url: str, session_id: str, dashboard_id: int, card_id: int
) -> None:
    r = session.post(
        f"{base_url}/api/dashboard/{dashboard_id}/cards",
        json={"cardId": card_id, "row": 0, "col": 0, "size_x": 12, "size_y": 6},
        headers=auth_headers(session_id),
        timeout=30,
    )
    r.raise_for_status()


def enable_public_sharing(session: Session, base_url: str, session_id: str) -> None:
    r = session.put(
        f"{base_url}/api/setting/enable-public-sharing",
        json={"value": True},
        headers=auth_headers(session_id),
        timeout=10,
    )
    r.raise_for_status()


def share_dashboard_publicly(
    session: Session, base_url: str, session_id: str, dashboard_id: int
) -> str:
    r = session.post(
        f"{base_url}/api/dashboard/{dashboard_id}/public_link",
        json={},
        headers=auth_headers(session_id),
        timeout=10,
    )
    r.raise_for_status()
    uuid = r.json()["uuid"]
    return f"{base_url}/public/dashboard/{uuid}"


def bootstrap(session: Session, cfg: BootstrapConfig) -> str | None:
    """Run the full provisioning flow. Returns the public dashboard URL,
    or None if Metabase has already been set up.
    """
    if not wait_for_metabase(session, cfg.base_url):
        raise RuntimeError("Metabase /api/health never returned 200.")

    token = fetch_setup_token(session, cfg.base_url)
    if token is None:
        return None  # already set up; idempotent no-op

    session_id, db_id = post_setup(session, cfg.base_url, build_setup_payload(token, cfg))
    if not session_id or db_id is None:
        raise RuntimeError("Metabase /api/setup did not return session_id + database id.")

    card_id = create_card(session, cfg.base_url, session_id, build_card_payload(db_id, cfg))
    dashboard_id = create_dashboard(session, cfg.base_url, session_id, build_dashboard_payload(cfg))
    add_card_to_dashboard(session, cfg.base_url, session_id, dashboard_id, card_id)

    enable_public_sharing(session, cfg.base_url, session_id)
    return share_dashboard_publicly(session, cfg.base_url, session_id, dashboard_id)
