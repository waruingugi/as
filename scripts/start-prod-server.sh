#!/bin/bash
# Purge the Celery queue
# Celery tasks that had failed when celery was down will not be re-tried.
# celery -A aviator purge -f
set -e

# Only needed for azure apps
# (sometimes 'python manage.py collectstatic' fails due to permission errors)
echo "Ensuring correct static file permissions..."
mkdir -p /home/api/static
chmod -R 755 /home/api/static

echo "Applying database migrations..."
python manage.py migrate

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting Gunicorn..."
exec gunicorn --workers=3 --bind=0.0.0.0:8000 aviator.wsgi:application
