#!/bin/sh
# Purge the Celery queue
# Celery tasks that had failed when celery was down will not be re-tried.
# celery -A aviator purge -f
set -e

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "Applying database migrations..."
python manage.py migrate

echo "Starting Gunicorn..."
gunicorn aviator.wsgi --bind 0.0.0.0:8000 --timeout 60 --access-logfile - --error-logfile -

