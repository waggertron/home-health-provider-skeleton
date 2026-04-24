"""Phase 4 domain-event publisher.

Every state change that matters for a live UI calls publish(tenant_id, event).
The event is JSON-encoded and PUBLISHed to channel tenant:{id}:events. A
separate Node gateway (rt-node) subscribes to that channel and forwards frames
to authenticated WebSocket clients.

Schema helpers build envelopes with a stable shape:
    { "type": "<dotted.event.name>", "tenant_id": N, "ts": ISO8601Z,
      "payload": {...} }
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

import redis
from django.conf import settings

logger = logging.getLogger(__name__)

_client: redis.Redis | None = None


def _get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(settings.EVENTS_REDIS_URL)
    return _client


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _envelope(event_type: str, tenant_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": event_type,
        "tenant_id": tenant_id,
        "ts": _now_iso(),
        "payload": payload,
    }


def channel_for(tenant_id: int) -> str:
    return f"tenant:{tenant_id}:events"


def publish(tenant_id: int, event: dict[str, Any]) -> None:
    """PUBLISH event as JSON on the tenant's events channel.

    Fault-tolerant: a Redis outage logs a warning but does not raise —
    event publishing is a best-effort fanout, not a correctness-critical
    step on the primary write path.
    """
    try:
        _get_client().publish(channel_for(tenant_id), json.dumps(event))
    except redis.RedisError as exc:
        logger.warning("events.publish failed for tenant=%s: %s", tenant_id, exc)


# --- Schema helpers ---------------------------------------------------------


def visit_reassigned(visit: Any) -> dict[str, Any]:
    return _envelope(
        "visit.reassigned",
        visit.tenant_id,
        {"visit_id": visit.id, "clinician_id": visit.clinician_id},
    )


def visit_status_changed(visit: Any) -> dict[str, Any]:
    return _envelope(
        "visit.status_changed",
        visit.tenant_id,
        {
            "visit_id": visit.id,
            "status": visit.status,
            "clinician_id": visit.clinician_id,
        },
    )


def schedule_optimized(tenant_id: int, date_iso: str, summary: dict[str, Any]) -> dict[str, Any]:
    return _envelope(
        "schedule.optimized",
        tenant_id,
        {"date": date_iso, **summary},
    )


def sms_delivered(sms: Any) -> dict[str, Any]:
    return _envelope(
        "sms.delivered",
        sms.tenant_id,
        {"sms_id": sms.id, "visit_id": sms.visit_id, "status": sms.status},
    )


def clinician_position_updated(position: Any) -> dict[str, Any]:
    return _envelope(
        "clinician.position_updated",
        position.tenant_id,
        {
            "clinician_id": position.clinician_id,
            "lat": position.lat,
            "lon": position.lon,
            "ts": position.ts.isoformat(),
        },
    )
