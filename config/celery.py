"""
Celery app configuration for WanderLeaf backend.

Uses Redis as broker. Run worker with:
    celery -A config worker -l info

For async payment-expiry timers per booking.
"""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("wanderleaf")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
