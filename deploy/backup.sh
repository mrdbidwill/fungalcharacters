#!/bin/bash
# Nightly database backup on the VPS (fc's crontab: 15 3 * * * /home/fc/app/deploy/backup.sh). Keeps 30 days.
set -euo pipefail
umask 077   # backups hold password hashes: readable by fc only
cd /home/fc/app
docker compose -f docker-compose.prod.yml exec -T db pg_dump -U fungalcharacters fungalcharacters \
  | gzip > /home/fc/backups/fungalcharacters_$(date +%F).sql.gz
find /home/fc/backups -name 'fungalcharacters_*.sql.gz' -mtime +30 -delete
# Remove expired sign-in sessions from the database.
docker compose -f docker-compose.prod.yml exec -T web python manage.py clearsessions
