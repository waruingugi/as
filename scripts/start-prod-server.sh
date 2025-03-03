#!/bin/bash
# Purge the Celery queue
# Celery tasks that had failed when celery was down will not be re-tried.
# celery -A aviator purge -f
set -e

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "Applying database migrations..."
python manage.py migrate
#
#echo "Starting Celery worker..."
#celery -A aviator worker --loglevel=info --concurrency=3 &
#
#echo "Starting Celery beat..."
#celery -A aviator beat --loglevel=info &


echo "Starting Gunicorn..."
exec gunicorn --workers=3 --bind=0.0.0.0:8000 aviator.wsgi:application --access-logfile - --error-logfile -

