#!/bin/bash
# Deploy the code from this Mac to the VPS and restart the site. Claude runs this.
# Usage: deploy/deploy.sh            (code update)
#        deploy/deploy.sh --restore DUMP.sql   (first launch: load a copy of the local database)
set -euo pipefail
cd "$(dirname "$0")/.."
HOST=fc@85.31.233.192
SSH="ssh -i $HOME/.ssh/fungalcharacters_deploy -o BatchMode=yes"
COMPOSE="docker compose -f docker-compose.prod.yml"
# macOS's rsync (openrsync) has no --chmod; standard permissions are set on the server after copying.
rsync -az --delete -e "$SSH" \
  --exclude .git --exclude .env --exclude node_modules --exclude __pycache__ --exclude staticfiles \
  ./ $HOST:/home/fc/app/
$SSH $HOST 'cd /home/fc/app && find . -path ./.env -prune -o -type d -exec chmod 755 {} + -o -type f -exec chmod 644 {} + && chmod +x deploy/*.sh && chmod 600 .env'

if [ "${1:-}" = "--restore" ]; then
  DUMP="$2"
  $SSH $HOST "cd /home/fc/app && $COMPOSE up -d --wait db"   # waits until the database is healthy
  $SSH $HOST "cd /home/fc/app && $COMPOSE exec -T db psql -v ON_ERROR_STOP=1 -q -U fungalcharacters -d fungalcharacters" < "$DUMP"
fi
$SSH $HOST "cd /home/fc/app && $COMPOSE up -d --build && $COMPOSE ps"
