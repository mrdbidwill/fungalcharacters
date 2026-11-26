#!/bin/bash
# Make a dated data release from the LIVE data and publish it (docs/RELEASING.md). Claude runs this, after Will's go.
# Usage: deploy/make_release.sh 1.1.0 "One-line notes for the changelog"
set -euo pipefail
cd "$(dirname "$0")/.."
VERSION="$1"; NOTES="${2:-}"; DATE=$(date +%F)
HOST=fc@85.31.233.192
SSH="ssh -i $HOME/.ssh/fungalcharacters_deploy -o BatchMode=yes"
COMPOSE="docker compose -f docker-compose.prod.yml"
[ -e "data/releases/$VERSION" ] && { echo "data/releases/$VERSION already exists"; exit 1; }
# 1. Build from the live database, inside the running app container (nothing in the database changes yet).
$SSH $HOST "cd /home/fc/app && $COMPOSE exec -T web sh -c 'rm -rf /tmp/release_build && mkdir /tmp/release_build && python manage.py make_release $VERSION --date $DATE --notes \"$NOTES\" --out /tmp/release_build' \
  && rm -rf /home/fc/release_build && $COMPOSE cp web:/tmp/release_build /home/fc/release_build"
# 2. Copy it into the repository on this Mac.
rsync -az -e "$SSH" $HOST:/home/fc/release_build/$VERSION/ data/releases/$VERSION/
find data/releases/$VERSION -type f -exec chmod 644 {} +
echo "Release $VERSION built into data/releases/$VERSION. Next: tests, commit, push, deploy/deploy.sh, then:"
echo "  $SSH $HOST \"cd /home/fc/app && $COMPOSE exec -T web python manage.py make_release $VERSION --date $DATE --notes '...' --record-only\""
