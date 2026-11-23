#!/usr/bin/env bash
# Staging helper. Run from the production worktree on TNV-server.
#   scripts/staging.sh up       build + start + migrate (+ seed on first run)
#   scripts/staging.sh seed     wipe staging data and re-seed the demo crawl
#   scripts/staging.sh down     stop (keeps the DB volume)
set -euo pipefail
cd "$(dirname "$0")/.."
ENVF="${STAGING_ENV:-$HOME/businesses/pub-crawl-staging/.env}"
DC=(docker compose -f deploy/staging/docker-compose.yml --env-file "$ENVF")
DBX=(docker exec -i pub-crawl-staging-db-1 sh -c 'mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" "$@" pub_crawl' sh)
seed() {
  set -a; . "$ENVF"; set +a
  sed -e "s/__OWNER_PW__/${STAGING_OWNER_PASSWORD}/g" -e "s/__REF_PW__/${STAGING_REF_PASSWORD}/g" \
      -e "s/__PLAYER_PW__/${STAGING_PLAYER_PASSWORD}/g" deploy/staging/seed.sql | "${DBX[@]}"
  echo seeded
}
case "${1:-up}" in
  up)
    "${DC[@]}" up -d --build db
    for i in $(seq 1 60); do docker exec pub-crawl-staging-db-1 healthcheck.sh --connect >/dev/null 2>&1 && break; sleep 2; done
    scripts/migrate.sh "${DBX[@]}"
    if [ "$(echo 'SELECT COUNT(*) FROM Event;' | "${DBX[@]}" -N)" = "0" ]; then seed; fi
    "${DC[@]}" up -d --build backend web
    "${DC[@]}" ps ;;
  seed) seed ;;
  down) "${DC[@]}" down ;;
  *) "${DC[@]}" "$@" ;;
esac
