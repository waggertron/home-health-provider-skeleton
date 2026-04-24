"""Celery plumbing sanity check.

Runs with CELERY_TASK_ALWAYS_EAGER=True (set in tests via pytest fixture)
so we don't need a running worker for pytest.
"""

from django.test import override_settings

from scheduling.tasks import ping


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
def test_ping_runs_eagerly_and_returns_pong():
    result = ping.delay()
    assert result.get(timeout=5) == "pong"


def test_ping_direct_call_works_without_celery():
    # Calling the task function directly should behave like any function.
    assert ping() == "pong"
