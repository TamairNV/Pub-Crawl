"""Per-event payments with Stripe Checkout.

Flow: an organiser (admin) presses "Unlock this crawl" -> POST /api/payments/checkout
creates a Checkout Session (payment mode, GBP) and returns its URL -> the browser goes
to Stripe -> Stripe calls POST /api/stripe/webhook with checkout.session.completed ->
we verify the signature and mark the event paid. The success page never marks anything
paid by itself; only the signed webhook does.

Env (root .env, names in .env.example): STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET,
APP_BASE_URL, optional PAYMENTS_ENFORCE=1 (free events limited to FREE_TEAM_LIMIT teams)
and STRIPE_ALLOW_LIVE=1 (live keys are refused without it).
Schema: migrations/0003_event_payments.sql. If it hasn't been run, every route here
reports payments as unavailable instead of failing.
"""
import json
import os
import uuid

import pymysql
import stripe
from flask import Blueprint, jsonify, request, session

from .SQL_manager import get_db, _close_conn
from .routes import admin_required, login_required, can_view_event

payments = Blueprint('payments', __name__)

# Prices in pence. Free events can have up to FREE_TEAM_LIMIT teams.
TIERS = {
  'group': {'amount': 999, 'label': 'Group crawl'},
  'society': {'amount': 1500, 'label': 'Society crawl'},
}
CURRENCY = 'gbp'
FREE_TEAM_LIMIT = 3
# Stripe product tax code. Required when Managed Payments (Stripe as merchant of record) is on for the
# account, and used by Stripe Tax otherwise. Default: General - Electronically Supplied Services.
TAX_CODE = os.getenv("STRIPE_TAX_CODE", "txcd_10000000")
PAID_EVENT_TYPES = ('checkout.session.completed', 'checkout.session.async_payment_succeeded')


def _stripe_ready():
  """Set the API key and return True if payments can be used (test keys only unless allowed)."""
  key = os.getenv('STRIPE_SECRET_KEY', '')
  if not key:
    return False
  if not key.startswith(('sk_test_', 'rk_test_')) and os.getenv('STRIPE_ALLOW_LIVE') != '1':
    print('payments: refusing a non-test Stripe key (set STRIPE_ALLOW_LIVE=1 to go live)')
    return False
  stripe.api_key = key
  return True


def _base_url():
  return os.getenv('APP_BASE_URL', 'https://crawl.tamairnv.co.uk').rstrip('/')


def _query(sql, args=None, one=False):
  connection = None
  try:
    connection = get_db()
    with connection.cursor() as cur:
      cur.execute(sql, args)
      rows = cur.fetchall()
    return (rows[0] if rows else None) if one else rows
  finally:
    _close_conn(connection)


def get_payment_state(event_id):
  """Paid state of one event, or None if the event doesn't exist. Raises if the schema is missing."""
  event = _query(
    "SELECT id, name, paid_at, paid_tier FROM Event WHERE id = %s AND deleted_at IS NULL",
    [event_id], one=True)
  if not event:
    return None
  teams = _query("SELECT COUNT(*) AS n FROM Team WHERE eventID = %s", [event_id], one=True)
  return {
    'event_name': event['name'],
    'paid': event['paid_at'] is not None,
    'tier': event['paid_tier'],
    'team_count': int(teams['n'] if teams else 0),
  }


def team_limit_reached(event_id):
  """True if adding a team should be refused: only when PAYMENTS_ENFORCE=1 and the event is free and full."""
  if os.getenv('PAYMENTS_ENFORCE') != '1':
    return False
  try:
    state = get_payment_state(event_id)
  except pymysql.MySQLError:
    return False  # migration not run: never block
  return bool(state) and not state['paid'] and state['team_count'] >= FREE_TEAM_LIMIT


@payments.route('/api/payments/status', methods=['POST'])
@login_required
def payment_status():
  data = request.get_json(silent=True) or {}
  event_id = str(data.get('event_id', ''))
  if not event_id or not can_view_event(event_id):
    return jsonify({"status": "failed", "received": "Forbidden"}), 403
  try:
    state = get_payment_state(event_id)
  except pymysql.MySQLError:
    return jsonify({"status": "success", "received": {"available": False}})
  if state is None:
    return jsonify({"status": "failed", "received": "No such crawl"}), 404
  state.pop('event_name')
  state.update({
    'available': _stripe_ready(),
    'free_team_limit': FREE_TEAM_LIMIT,
    'enforced': os.getenv('PAYMENTS_ENFORCE') == '1',
    'tiers': {k: {'amount': v['amount'], 'label': v['label']} for k, v in TIERS.items()},
    'currency': CURRENCY,
  })
  return jsonify({"status": "success", "received": state})


@payments.route('/api/payments/checkout', methods=['POST'])
@admin_required
def create_checkout():
  if not _stripe_ready():
    return jsonify({"status": "failed", "received": "Payments are not set up"}), 503
  data = request.get_json(silent=True) or {}
  event_id = str(data.get('event_id', ''))
  tier = str(data.get('tier', ''))
  if tier not in TIERS:
    return jsonify({"status": "failed", "received": "Unknown tier"}), 400
  try:
    state = get_payment_state(event_id)
  except pymysql.MySQLError:
    return jsonify({"status": "failed", "received": "Payments are not set up"}), 503
  if state is None:
    return jsonify({"status": "failed", "received": "No such crawl"}), 404
  if state['paid']:
    return jsonify({"status": "failed", "received": "This crawl is already unlocked"}), 409

  # Reuse a still-open session for the same event and tier instead of making a new one.
  existing = _query(
    "SELECT stripe_session_id FROM EventPayment WHERE event_id = %s AND tier = %s AND status = 'open' "
    "AND created_at > NOW() - INTERVAL 23 HOUR ORDER BY created_at DESC LIMIT 1",
    [event_id, tier], one=True)
  if existing:
    try:
      old = stripe.checkout.Session.retrieve(existing['stripe_session_id'])
      if old.status == 'open' and old.url:
        return jsonify({"status": "success", "received": {"url": old.url}})
    except stripe.StripeError as e:
      print(f"payments: could not reuse session: {e}")

  price = TIERS[tier]
  base = _base_url()
  meta = {'event_id': event_id, 'tier': tier, 'user_id': str(session.get('user_id', ''))}
  try:
    checkout = stripe.checkout.Session.create(
      mode='payment',
      line_items=[{
        'quantity': 1,
        'price_data': {
          'currency': CURRENCY,
          'unit_amount': price['amount'],
          'product_data': {
            'name': f"Pub Crawl: {price['label']}",
            'description': f"Unlimited teams for \"{state['event_name']}\""[:250],
            'tax_code': TAX_CODE,
          },
        },
      }],
      client_reference_id=event_id,
      metadata=meta,
      payment_intent_data={'metadata': meta},
      success_url=f"{base}/event-details/{event_id}?paid=1",
      cancel_url=f"{base}/event-details/{event_id}?paid=0",
    )
  except stripe.StripeError as e:
    print(f"payments: checkout create failed: {e}")
    return jsonify({"status": "failed", "received": "Could not start the payment"}), 502

  connection = None
  try:
    connection = get_db()
    with connection.cursor() as cur:
      cur.execute(
        "INSERT INTO EventPayment (id, event_id, stripe_session_id, tier, amount_total, currency, status, created_by) "
        "VALUES (%s, %s, %s, %s, %s, %s, 'open', %s)",
        [str(uuid.uuid4()), event_id, checkout.id, tier, price['amount'], CURRENCY, meta['user_id'] or None])
    connection.commit()
  finally:
    _close_conn(connection)
  return jsonify({"status": "success", "received": {"url": checkout.url}})


def mark_paid(stripe_event_id, event_type, obj):
  """Mark the event paid from a verified Checkout Session. Idempotent; returns a short result string."""
  event_id = (obj.get('metadata') or {}).get('event_id') or obj.get('client_reference_id')
  tier = (obj.get('metadata') or {}).get('tier')
  session_id = obj.get('id')
  amount = obj.get('amount_total')
  subtotal = obj.get('amount_subtotal', amount)  # before any tax Stripe adds
  currency = (obj.get('currency') or '').lower()
  if not event_id or tier not in TIERS:
    return 'ignored: no event or tier'
  if subtotal != TIERS[tier]['amount'] or currency != CURRENCY:
    return f'ignored: amount {subtotal} {currency} does not match {tier}'

  connection = get_db()
  try:
    with connection.cursor() as cur:
      cur.execute("INSERT IGNORE INTO StripeWebhookEvent (id, type) VALUES (%s, %s)", [stripe_event_id, event_type])
      if cur.rowcount == 0:
        connection.rollback()
        return 'duplicate'
      cur.execute("SELECT id FROM Event WHERE id = %s", [event_id])
      if not cur.fetchone():
        connection.commit()
        return 'ignored: unknown event'
      cur.execute(
        "UPDATE EventPayment SET status = 'paid', paid_at = NOW(), stripe_payment_intent = %s, amount_total = %s "
        "WHERE stripe_session_id = %s",
        [obj.get('payment_intent'), amount, session_id])
      if cur.rowcount == 0:
        cur.execute(
          "INSERT INTO EventPayment (id, event_id, stripe_session_id, stripe_payment_intent, tier, amount_total, "
          "currency, status, paid_at) VALUES (%s, %s, %s, %s, %s, %s, %s, 'paid', NOW())",
          [str(uuid.uuid4()), event_id, session_id, obj.get('payment_intent'), tier, amount, currency])
      cur.execute(
        "UPDATE Event SET paid_at = COALESCE(paid_at, NOW()), paid_tier = COALESCE(paid_tier, %s) WHERE id = %s",
        [tier, event_id])
    connection.commit()
    return 'paid'
  except Exception:
    connection.rollback()  # the dedupe row goes too, so Stripe's retry gets another go
    raise
  finally:
    _close_conn(connection)


def mark_expired(obj):
  connection = get_db()
  try:
    with connection.cursor() as cur:
      cur.execute("UPDATE EventPayment SET status = 'expired' WHERE stripe_session_id = %s AND status = 'open'",
                  [obj.get('id')])
    connection.commit()
  finally:
    _close_conn(connection)


@payments.route('/api/stripe/webhook', methods=['POST'])
def stripe_webhook():
  secret = os.getenv('STRIPE_WEBHOOK_SECRET', '')
  if not secret:
    return jsonify({"status": "failed", "received": "Webhook not configured"}), 503
  payload = request.get_data()
  try:
    stripe.Webhook.construct_event(payload, request.headers.get('Stripe-Signature', ''), secret)
  except (ValueError, stripe.SignatureVerificationError):
    return jsonify({"status": "failed", "received": "Bad signature"}), 400

  event = json.loads(payload)
  event_type = event.get('type', '')
  obj = (event.get('data') or {}).get('object') or {}
  try:
    if event_type in PAID_EVENT_TYPES and obj.get('payment_status') == 'paid':
      result = mark_paid(event.get('id'), event_type, obj)
    elif event_type in ('checkout.session.expired', 'checkout.session.async_payment_failed'):
      mark_expired(obj)
      result = 'expired'
    else:
      result = 'ignored'
  except pymysql.MySQLError as e:
    print(f"payments: webhook DB error: {e}")
    return jsonify({"status": "failed", "received": "Try again"}), 500
  print(f"payments: webhook {event.get('id')} {event_type}: {result}")
  return jsonify({"status": "success", "received": result})
