#!/usr/bin/env bash
# Real Stripe TEST-mode end-to-end run against a THROWAWAY MariaDB (never the live DB, no ports published).
# Keys come from the vault via keys_run.py (KEYS_APP_TOKEN in .env, token "pub-crawl").
# Usage, from the repo root on TNV-server:  scripts/e2e-stripe.sh   then pay the URL in out/checkout_url.txt
# with card 4242 4242 4242 4242, any future expiry, any CVC. Output: /tmp/pc-e2e/out/result.txt
set -euo pipefail
cd "$(dirname "$0")/.."
NET=pc-e2e-net; DB=pc-e2e-db; APPC=pc-e2e-app; W=/tmp/pc-e2e
STRIPE_BIN="$(readlink -f ~/.local/lib/node_modules/@stripe/cli/node_modules/@stripe/cli-linux-x64/bin/stripe)"
cleanup() { docker rm -f "$APPC" "$DB" >/dev/null 2>&1 || true; docker network rm "$NET" >/dev/null 2>&1 || true; rm -f "$W/token.env"; }
trap cleanup EXIT
cleanup
rm -rf "$W" && mkdir -p "$W/out" "$W/src" && chmod 700 "$W"
tar --exclude=uploads --exclude=node_modules --exclude=venv --exclude=.git --exclude='*.key' --exclude='.env' --exclude='.evn' \
  --exclude=__pycache__ -cf - flask-backend migrations scripts | tar -x -C "$W/src"
cp ~/keys/client/keys_run.py "$W/keys_run.py"
( umask 077; grep -E '^KEYS_APP_TOKEN=' .env > "$W/token.env" )
docker network create "$NET" >/dev/null
docker run -d --name "$DB" --network "$NET" -e MARIADB_ROOT_PASSWORD=e2e -e MARIADB_DATABASE=pub_crawl_e2e mariadb:10.11 >/dev/null
for i in $(seq 1 60); do docker exec "$DB" healthcheck.sh --connect >/dev/null 2>&1 && break; sleep 1; done
docker create --name "$APPC" --network "$NET" --env-file "$W/token.env" -e KEYS_URL=http://keys:8001 \
  -e DB_HOST="$DB" -e DB_USER=root -e DB_PASSWORD=e2e -e DB_NAME=pub_crawl_e2e -e DB_PORT=3306 \
  -e SECRET_KEY=e2e-only -e PYTHONUNBUFFERED=1 -e APP_BASE_URL=https://crawl.tamairnv.co.uk \
  -v "$W/src":/e2e-src:ro -v "$W/out":/e2e/out -v "$W/keys_run.py":/e2e/keys_run.py:ro -v "$STRIPE_BIN":/usr/local/bin/stripe:ro \
  python:3.11-slim sh -c 'mkdir -p /work && cp -r /e2e-src/flask-backend /e2e-src/migrations /work/ && cp -r /e2e-src/scripts /e2e/scripts &&
    pip install -q --no-cache-dir --root-user-action=ignore -r /work/flask-backend/requirements.txt 2>&1 | grep -v "^\[notice\]" || true;
    exec python /e2e/keys_run.py sh /e2e/scripts/e2e_stripe_run.sh' >/dev/null
docker network connect keys-net "$APPC"
rm -f "$W/token.env"
docker start -a "$APPC"
