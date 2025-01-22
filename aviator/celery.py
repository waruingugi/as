from __future__ import absolute_import, unicode_literals

import os

from celery import Celery
from celery.schedules import crontab
from django.conf import settings

# Set the default Django settings module for the 'celery' program
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aviator.settings")

app = Celery(
    __name__, timezone="Africa/Nairobi", broker_connection_retry_on_startup=True
)

# Configure Celery using settings from Django settings.py
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load tasks from all registered Django configs.
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


# Period tasks in the system
app.conf.beat_schedule = {
    "identify_similar_workers": {
        # Task name which we have created in quiz.tasks
        "task": "identify_similar_workers",
        # Run every 3 minutes
        "schedule": crontab(minute="*/3"),
    },
}
