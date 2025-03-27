from __future__ import absolute_import, unicode_literals

import os

from celery import Celery
from celery.schedules import crontab
from django.conf import settings

# Set the default Django settings module for the 'celery' program
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aviator.settings")

app = Celery(__name__, broker_connection_retry_on_startup=False)

# Configure Celery using settings from Django settings.py
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load tasks from all registered Django configs.
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


# Period tasks in the system
app.conf.beat_schedule = {
    "identify_similar_workers_task": {
        "task": "orchestrator.tasks.identify_similar_workers",
        "schedule": crontab(minute="*/3"),
    },
    "find_failing_workers_task": {
        "task": "orchestrator.tasks.find_failing_workers",
        "schedule": crontab(minute="*/1"),
    },
}
