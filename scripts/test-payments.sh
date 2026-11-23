#!/usr/bin/env bash
# Run the payments tests against a THROWAWAY MariaDB (never the live DB, no ports published).
# Usage: scripts/test-payments.sh   (from the repo root, on TNV-server)
set -euo pipefail
cd "$(dirname "$0")/.."
NET=pc-paytest-net; DB=pc-paytest-db
cleanup() { docker rm -f "$DB" >/dev/null 2>&1 || true; docker network rm "$NET" >/dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup
docker network create "$NET" >/dev/null
docker run -d --name "$DB" --network "$NET" -e MARIADB_ROOT_PASSWORD=paytest -e MARIADB_DATABASE=pub_crawl_test mariadb:10.11 >/dev/null
for i in $(seq 1 60); do docker exec "$DB" healthcheck.sh --connect >/dev/null 2>&1 && break; sleep 1; done
docker run --rm --network "$NET" -v "$PWD":/src:ro -w /work \
  -e PAYMENTS_TEST_DB=1 -e SECRET_KEY=test-only-not-secret -e DB_HOST="$DB" -e DB_USER=root -e DB_PASSWORD=paytest -e DB_NAME=pub_crawl_test -e DB_PORT=3306 \
  python:3.11-slim sh -c '
    tar -C /src --exclude=venv --exclude=".env" --exclude=".evn" --exclude=__pycache__ -cf - flask-backend migrations | tar -C /work -xf - &&
    pip install -q --no-cache-dir --root-user-action=ignore -r /work/flask-backend/requirements.txt pytest 2>&1 | grep -v "^\[notice\]" || true
    cd /work/flask-backend && python -m pytest -q tests/test_payments.py'
