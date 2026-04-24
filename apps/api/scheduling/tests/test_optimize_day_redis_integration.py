"""optimize_day publishes events that real Redis subscribers receive."""

import json
import time
from datetime import UTC, date, datetime, timedelta

import pytest
import redis
from django.conf import settings
from django.test import override_settings

from accounts.models import Role, User
from clinicians.models import Clinician, Credential
from core import events
from core.events import channel_for
from patients.models import Patient
from scheduling.tasks import optimize_day
from tenancy.models import Tenant
from visits.models import Visit


@pytest.fixture
def optimize_redis_fixture(db):
    tenant = Tenant.objects.create(name="Westside", timezone="UTC")
    u = User.objects.create_user(
        email="rn@x.demo", password="p", tenant=tenant, role=Role.CLINICIAN
    )
    Clinician.objects.create(
        user=u, tenant=tenant, credential=Credential.RN, home_lat=34.0, home_lon=-118.0
    )
    patient = Patient.objects.create(
        tenant=tenant,
        name="P",
        phone="+1",
        address="x",
        lat=34.01,
        lon=-118.0,
        required_skill=Credential.RN,
    )
    day_start = datetime(2026, 4, 24, 9, 0, tzinfo=UTC)
    Visit.objects.create(
        tenant=tenant,
        patient=patient,
        window_start=day_start,
        window_end=day_start + timedelta(hours=2),
        required_skill=Credential.RN,
    )
    return tenant, date(2026, 4, 24)


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
    events._client = None
    yield
    events._client = None


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
def test_optimize_day_schedule_optimized_reaches_real_redis(optimize_redis_fixture, redis_client):
    tenant, the_day = optimize_redis_fixture
    pubsub = redis_client.pubsub()
    pubsub.subscribe(channel_for(tenant.id))
    # Drain subscribe confirmation.
    pubsub.get_message(timeout=1.0)

    optimize_day.delay(tenant.id, the_day.isoformat(), time_budget_s=1).get(timeout=15)

    types_seen: list[str] = []
    deadline = time.time() + 2.0
    while time.time() < deadline and "schedule.optimized" not in types_seen:
        msg = pubsub.get_message(timeout=0.1, ignore_subscribe_messages=True)
        if msg:
            types_seen.append(json.loads(msg["data"])["type"])
    assert "schedule.optimized" in types_seen
    pubsub.unsubscribe()
    pubsub.close()
