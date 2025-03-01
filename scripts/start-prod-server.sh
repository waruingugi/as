#!/bin/bash
# Purge the Celery queue
# Celery tasks that had failed when celery was down will not be re-tried.
# celery -A aviator purge -f
set -e

echo "Applying database migrations..."
python manage.py migrate

echo "Starting Gunicorn..."
exec gunicorn --workers=3 --bind=0.0.0.0:8000 aviator.wsgi:application
