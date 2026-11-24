#!/usr/bin/env bash
# Nightly gzip dump of the STAGING crawl DB (from its own container), kept for 14 days.
#   cron: 15 4 * * * ~/businesses/pub-crawl-production/scripts/backup-db.sh staging
# The live DB backup (host MariaDB, needs a read-only dump user) is in the go-live plan.
set -euo pipefail
target="${1:-staging}"
dir="$HOME/backups/pub-crawl-db/$target"; mkdir -p "$dir"; chmod 700 "$dir"
stamp=$(date +%Y%m%d-%H%M%S)
case "$target" in
  staging)
    docker exec pub-crawl-staging-db-1 sh -c 'mariadb-dump -uroot -p"$MARIADB_ROOT_PASSWORD" --single-transaction --routines pub_crawl' \
      | gzip > "$dir/pub_crawl_$stamp.sql.gz.part" ;;
  *) echo "unknown target $target" >&2; exit 2 ;;
esac
mv "$dir/pub_crawl_$stamp.sql.gz.part" "$dir/pub_crawl_$stamp.sql.gz"
chmod 600 "$dir/pub_crawl_$stamp.sql.gz"
find "$dir" -name 'pub_crawl_*.sql.gz' -mtime +14 -delete
echo "backup ok: $dir/pub_crawl_$stamp.sql.gz ($(du -h "$dir/pub_crawl_$stamp.sql.gz" | cut -f1))"
