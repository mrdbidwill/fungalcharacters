#!/bin/sh
# Production start: apply migrations, collect static files, run gunicorn.
set -e
python manage.py migrate --noinput
python manage.py createcachetable
python manage.py collectstatic --noinput -v 0
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 60 \
     --access-logfile - --error-logfile - --forwarded-allow-ips="*"
