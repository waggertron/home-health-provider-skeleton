"""Multi-schema OLTP/OLAP separation (post-v1 #3).

The reporting tables now live in the `reporting` schema; a
`metabase_ro` Postgres role has USAGE on that schema and SELECT on its
tables but no access to anything in `public`. These tests open a fresh
connection as `metabase_ro` and exercise both sides of the boundary.
"""

from __future__ import annotations

import psycopg
import pytest
from django.conf import settings
from django.db import connection


def _metabase_dsn() -> dict:
    db = settings.DATABASES["default"]
    return {
        "host": db["HOST"],
        "port": db["PORT"],
        "dbname": connection.settings_dict["NAME"],
        "user": "metabase_ro",
        "password": "metabase_ro_demo",
    }


@pytest.mark.django_db
def test_reporting_schema_exists_and_holds_the_two_rollup_tables():
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'reporting'
            ORDER BY table_name
            """
        )
        names = [r[0] for r in cur.fetchall()]
    assert names == ["daily_agency_stats", "daily_clinician_stats"]


@pytest.mark.django_db
def test_metabase_ro_can_select_from_reporting_tables():
    with psycopg.connect(**_metabase_dsn()) as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM reporting.daily_agency_stats")
        row = cur.fetchone()
        assert row is not None and row[0] >= 0  # empty is fine; access is the point
        cur.execute("SELECT count(*) FROM reporting.daily_clinician_stats")
        row = cur.fetchone()
        assert row is not None and row[0] >= 0


@pytest.mark.django_db
def test_metabase_ro_cannot_read_core_tables():
    with (
        psycopg.connect(**_metabase_dsn()) as conn,
        conn.cursor() as cur,
        pytest.raises(psycopg.errors.InsufficientPrivilege),
    ):
        cur.execute("SELECT count(*) FROM visits_visit")


@pytest.mark.django_db
def test_metabase_ro_cannot_write_to_reporting_tables():
    with (
        psycopg.connect(**_metabase_dsn()) as conn,
        conn.cursor() as cur,
        pytest.raises(psycopg.errors.InsufficientPrivilege),
    ):
        cur.execute(
            "INSERT INTO reporting.daily_agency_stats "
            "(tenant_id, date, visits_completed, missed_count, on_time_pct, "
            "sms_sent, sms_delivered, rolled_at) "
            "VALUES (1, '2026-04-28', 0, 0, 0.0, 0, 0, NOW())"
        )
