#!/bin/sh
# Purge the Celery queue
# Celery tasks that had failed when celery was down will not be re-tried.
# celery -A majibu purge -f
python manage.py migrate
python manage.py collectstatic --no-input
gunicorn majibu.wsgi --bind 0.0.0.0:8000 --timeout 60 --access-logfile - --error-logfile -
