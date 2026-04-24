"""Integration tests for core.events — real Redis round-trip + resilience.

Requires a running Redis (via `make up` or `docker compose up -d cache-redis`).
"""

import json
import logging
import time
from unittest.mock import patch

import pytest
import redis
from django.conf import settings
from django.test import override_settings

from core import events
from core.events import channel_for, publish, visit_status_changed


def _drain_subscribe(pubsub: redis.client.PubSub, n: int = 1) -> None:
    """Drain n SUBSCRIBE-confirmation frames so the queue is ready for data."""
    for _ in range(n):
        pubsub.get_message(timeout=1.0)


@pytest.fixture
def redis_client():
    client = redis.Redis.from_url(settings.EVENTS_REDIS_URL, socket_timeout=2.0)
    try:
        client.ping()
    except redis.RedisError:
        pytest.skip("Redis not reachable — run `make up` first.")
    yield client
    client.close()


@pytest.fixture(autouse=True)
def reset_events_client():
    """Force core.events to lazy-init a fresh client per test (so override_settings bites)."""
    events._client = None
    yield
    events._client = None


def test_publish_reaches_real_redis_subscriber(redis_client):
    pubsub = redis_client.pubsub()
    pubsub.subscribe(channel_for(999))
    _drain_subscribe(pubsub)

    publish(999, {"type": "integration.ping", "tenant_id": 999, "payload": {"x": 1}})

    msg = None
    deadline = time.time() + 2.0
    while time.time() < deadline:
        msg = pubsub.get_message(timeout=0.1, ignore_subscribe_messages=True)
        if msg:
            break
    assert msg is not None, "no message received within 2s"
    assert msg["channel"].decode() == "tenant:999:events"
    decoded = json.loads(msg["data"])
    assert decoded["type"] == "integration.ping"
    assert decoded["payload"] == {"x": 1}
    pubsub.unsubscribe()
    pubsub.close()


def test_channels_are_tenant_isolated(redis_client):
    """A subscriber on tenant 1 must never see tenant 2's events."""
    pubsub = redis_client.pubsub()
    pubsub.subscribe(channel_for(1))
    _drain_subscribe(pubsub)

    publish(2, {"type": "noise", "tenant_id": 2, "payload": {}})
    publish(1, {"type": "intended", "tenant_id": 1, "payload": {}})

    received_types: list[str] = []
    deadline = time.time() + 1.5
    while time.time() < deadline:
        msg = pubsub.get_message(timeout=0.1, ignore_subscribe_messages=True)
        if msg:
            received_types.append(json.loads(msg["data"])["type"])
    assert received_types == ["intended"]
    pubsub.unsubscribe()
    pubsub.close()


def test_multiple_subscribers_each_receive(redis_client):
    a = redis_client.pubsub()
    b = redis_client.pubsub()
    a.subscribe(channel_for(42))
    b.subscribe(channel_for(42))
    _drain_subscribe(a)
    _drain_subscribe(b)

    publish(42, {"type": "fan.out", "tenant_id": 42, "payload": {}})

    def await_one(ps):
        deadline = time.time() + 2.0
        while time.time() < deadline:
            msg = ps.get_message(timeout=0.1, ignore_subscribe_messages=True)
            if msg:
                return msg
        return None

    ma, mb = await_one(a), await_one(b)
    assert ma is not None and mb is not None
    assert json.loads(ma["data"])["type"] == "fan.out"
    assert json.loads(mb["data"])["type"] == "fan.out"
    a.unsubscribe()
    b.unsubscribe()
    a.close()
    b.close()


def test_publish_with_redis_down_logs_and_does_not_raise(caplog):
    """Point at a port nothing listens on; publish must not raise."""
    with override_settings(EVENTS_REDIS_URL="redis://127.0.0.1:1/0"):
        events._client = None  # force re-init against bad URL
        with caplog.at_level(logging.WARNING, logger="core.events"):
            publish(1, {"type": "t", "tenant_id": 1, "payload": {}})
    assert any("publish failed" in r.message.lower() for r in caplog.records)


def test_publish_survives_redis_error_from_client(caplog):
    """Even a non-connection RedisError (e.g. timeout) is swallowed."""
    with patch("core.events._get_client") as get:
        get.return_value.publish.side_effect = redis.TimeoutError("boom")
        with caplog.at_level(logging.WARNING, logger="core.events"):
            publish(1, {"type": "t", "tenant_id": 1, "payload": {}})
    assert any("publish failed" in r.message.lower() for r in caplog.records)


def test_real_subscriber_receives_schema_helper_envelope(redis_client, db):
    """End-to-end envelope: schema helper → publish → decode on the wire."""
    from types import SimpleNamespace

    pubsub = redis_client.pubsub()
    pubsub.subscribe(channel_for(7))
    _drain_subscribe(pubsub)

    visit = SimpleNamespace(id=1, tenant_id=7, clinician_id=3, status="on_site")
    publish(7, visit_status_changed(visit))

    msg = None
    deadline = time.time() + 2.0
    while time.time() < deadline:
        msg = pubsub.get_message(timeout=0.1, ignore_subscribe_messages=True)
        if msg:
            break
    assert msg is not None
    body = json.loads(msg["data"])
    assert body["type"] == "visit.status_changed"
    assert body["tenant_id"] == 7
    assert body["payload"]["visit_id"] == 1
    assert body["payload"]["status"] == "on_site"
    pubsub.unsubscribe()
    pubsub.close()
