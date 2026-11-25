#!/bin/bash
# Nightly database backup on the VPS (fc's crontab: 15 3 * * * /home/fc/app/deploy/backup.sh). Keeps 30 days.
set -euo pipefail
cd /home/fc/app
docker compose -f docker-compose.prod.yml exec -T db pg_dump -U fungalcharacters fungalcharacters \
  | gzip > /home/fc/backups/fungalcharacters_$(date +%F).sql.gz
find /home/fc/backups -name 'fungalcharacters_*.sql.gz' -mtime +30 -delete
