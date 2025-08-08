#!/bin/sh
# Purge the Celery queue
# Celery tasks that had failed when celery was down will not be re-tried.
# celery -A aviator purge -f
set -e

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "Applying database migrations..."
python manage.py migrate

#echo "Starting Gunicorn..."
#gunicorn aviator.wsgi --bind 0.0.0.0:8000 --timeout 60 --access-logfile - --error-logfile -

# Use daphne for ASGI applications (because we have WebSocket support)
# Otherwise use gunicorn for WSGI applications (uncomment the gunicorn line above)
echo "Starting Daphne..."
daphne --bind 0.0.0.0 -p 8000 aviator.asgi:application

