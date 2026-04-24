"""Celery application wiring.

The app object is imported from `hhps/__init__.py` so every `@shared_task`
defined under any INSTALLED_APP auto-registers.
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hhps.settings")

app = Celery("hhps")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
