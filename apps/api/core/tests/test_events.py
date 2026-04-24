import json
import re
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from core.events import (
    channel_for,
    clinician_position_updated,
    publish,
    schedule_optimized,
    sms_delivered,
    visit_reassigned,
    visit_status_changed,
)

ISO_Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")


def test_channel_for_follows_tenant_pattern():
    assert channel_for(42) == "tenant:42:events"


def test_publish_publishes_json_on_tenant_channel():
    event = {"type": "x", "tenant_id": 1, "ts": "now", "payload": {"k": 1}}
    with patch("core.events._get_client") as mock:
        client = MagicMock()
        mock.return_value = client
        publish(1, event)
        channel, body = client.publish.call_args[0]
        assert channel == "tenant:1:events"
        assert json.loads(body) == event


def test_visit_reassigned_envelope_shape():
    visit = SimpleNamespace(id=42, tenant_id=1, clinician_id=7)
    env = visit_reassigned(visit)
    assert env["type"] == "visit.reassigned"
    assert env["tenant_id"] == 1
    assert env["payload"] == {"visit_id": 42, "clinician_id": 7}
    assert ISO_Z.match(env["ts"])


def test_visit_status_changed_includes_status_and_clinician():
    visit = SimpleNamespace(id=3, tenant_id=2, clinician_id=None, status="on_site")
    env = visit_status_changed(visit)
    assert env["type"] == "visit.status_changed"
    assert env["tenant_id"] == 2
    assert env["payload"] == {"visit_id": 3, "status": "on_site", "clinician_id": None}


def test_schedule_optimized_merges_summary_with_date():
    env = schedule_optimized(1, "2026-04-24", {"routes": 3, "unassigned": 0})
    assert env["type"] == "schedule.optimized"
    assert env["tenant_id"] == 1
    assert env["payload"] == {"date": "2026-04-24", "routes": 3, "unassigned": 0}


def test_sms_delivered_envelope_shape():
    sms = SimpleNamespace(id=11, tenant_id=5, visit_id=99, status="delivered")
    env = sms_delivered(sms)
    assert env["type"] == "sms.delivered"
    assert env["tenant_id"] == 5
    assert env["payload"] == {"sms_id": 11, "visit_id": 99, "status": "delivered"}


def test_clinician_position_updated_envelope_shape():
    ts = datetime(2026, 4, 24, 10, 0, tzinfo=UTC)
    pos = SimpleNamespace(tenant_id=1, clinician_id=7, lat=34.0, lon=-118.0, ts=ts)
    env = clinician_position_updated(pos)
    assert env["type"] == "clinician.position_updated"
    assert env["payload"]["clinician_id"] == 7
    assert env["payload"]["lat"] == 34.0
    assert env["payload"]["lon"] == -118.0
    assert env["payload"]["ts"].startswith("2026-04-24T10:00:00")


def test_publish_round_trip_encodes_full_envelope():
    env = schedule_optimized(1, "2026-04-24", {"routes": 2, "unassigned": 1})
    with patch("core.events._get_client") as mock:
        client = MagicMock()
        mock.return_value = client
        publish(1, env)
        _, body = client.publish.call_args[0]
        decoded = json.loads(body)
        assert decoded == env
