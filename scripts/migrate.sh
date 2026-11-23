#!/usr/bin/env bash
# Apply numbered migrations in migrations/ (NNNN_name.sql, in order) and record them in schema_migrations.
# Every file must be safe to run twice (IF NOT EXISTS etc).
# Usage: scripts/migrate.sh <command that runs a mariadb client reading SQL on stdin>
#   staging: scripts/migrate.sh docker exec -i pub-crawl-staging-db-1 sh -c 'mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" "$@" pub_crawl' sh
# NEVER point this at the live DB without Tamair's go-ahead.
set -euo pipefail
cd "$(dirname "$0")/.."
[ $# -gt 0 ] || { echo "usage: $0 <mariadb client command>" >&2; exit 2; }
echo "CREATE TABLE IF NOT EXISTS schema_migrations (name VARCHAR(255) PRIMARY KEY, applied_at DATETIME DEFAULT CURRENT_TIMESTAMP);" | "$@"
applied="$(echo 'SELECT name FROM schema_migrations;' | "$@" -N)"
for f in migrations/[0-9][0-9][0-9][0-9]_*.sql; do
  n="$(basename "$f")"
  if grep -qx "$n" <<<"$applied"; then echo "skip  $n"; continue; fi
  { cat "$f"; echo; echo "INSERT INTO schema_migrations (name) VALUES ('$n');"; } | "$@"
  echo "apply $n"
done
