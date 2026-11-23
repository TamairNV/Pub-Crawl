#!/bin/sh
# Runs inside the e2e container, started through keys_run.py so the Stripe keys come from the vault.
set -eu
mkdir -p /e2e/out
case "${STRIPE_SECRET_KEY:-}" in
  sk_test_*|rk_test_*) ;;
  *) echo "[e2e] STRIPE_SECRET_KEY missing or not a test key; stopping"; exit 1 ;;
esac
export STRIPE_API_KEY="$STRIPE_SECRET_KEY"
STRIPE_WEBHOOK_SECRET="$(stripe listen --print-secret)"
export STRIPE_WEBHOOK_SECRET
echo "[e2e] got a stripe listen webhook secret (not printed)"

python /e2e/scripts/e2e_stripe_driver.py setup
cd /work/flask-backend
python -c "from app import create_app; create_app().run(host='127.0.0.1', port=8001)" > /e2e/out/app.log 2>&1 &
stripe listen --forward-to 127.0.0.1:8001/api/stripe/webhook \
  --events checkout.session.completed,checkout.session.async_payment_succeeded,checkout.session.expired,checkout.session.async_payment_failed \
  > /e2e/out/listen.log 2>&1 &
sleep 6
python /e2e/scripts/e2e_stripe_driver.py run

echo "[e2e] stripe trigger checkout.session.completed (fixture event, no crawl metadata: should be ignored)"
stripe trigger checkout.session.completed > /e2e/out/trigger.log 2>&1 || true
sleep 8
grep -E "payments: webhook" /e2e/out/app.log | tail -5 | tee -a /e2e/out/result.txt
grep -E "<--  \[" /e2e/out/listen.log | tail -6 | tee -a /e2e/out/result.txt
echo "[e2e] done"
