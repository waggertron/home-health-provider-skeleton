"""Celery tasks. Phase 3 T1 only has a ping task; later tasks add VRP solve."""

from celery import shared_task


@shared_task(name="scheduling.ping")
def ping() -> str:
    """Round-trip sanity task. Returns 'pong'."""
    return "pong"
