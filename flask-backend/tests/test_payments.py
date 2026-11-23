"""Payments tests against a throwaway MariaDB. Run with scripts/test-payments.sh (never the live DB).

Stripe's API is stubbed for Checkout creation; webhooks are signed exactly like Stripe signs
them (HMAC-SHA256 over "<t>.<payload>"), so signature checks run for real.
"""
import hashlib
import hmac
import json
import os
import time
import types
import uuid

import pymysql
import pytest

if os.getenv('PAYMENTS_TEST_DB') != '1':
  pytest.skip('needs the throwaway DB from scripts/test-payments.sh', allow_module_level=True)

WHSEC = 'whsec_test_local_only'
os.environ.update({'STRIPE_SECRET_KEY': 'sk_test_dummy', 'STRIPE_WEBHOOK_SECRET': WHSEC,
                   'APP_BASE_URL': 'https://crawl.example.test'})

from app import create_app  # noqa: E402
from app import payments as pay  # noqa: E402
from app.SQL_manager import get_db  # noqa: E402

HERE = os.path.dirname(__file__)
SCHEMA = """
CREATE TABLE IF NOT EXISTS Event (id char(36) NOT NULL DEFAULT uuid(), name varchar(255) NOT NULL,
  created_at datetime DEFAULT current_timestamp(), updated_at datetime DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  locked tinyint(1), points_inversed tinyint(1), current_pub_id varchar(64),
  awards_voting_open tinyint(1) NOT NULL DEFAULT 1, awards_results_visible tinyint(1) NOT NULL DEFAULT 0,
  deleted_at datetime, PRIMARY KEY (id));
CREATE TABLE IF NOT EXISTS Team (id char(36) NOT NULL DEFAULT uuid(), name varchar(255), colour varchar(50),
  created_at datetime DEFAULT current_timestamp(), updated_at datetime DEFAULT current_timestamp(), eventID char(36),
  PRIMARY KEY (id), CONSTRAINT fk_team_event FOREIGN KEY (eventID) REFERENCES Event (id));
CREATE TABLE IF NOT EXISTS User (id char(36) NOT NULL DEFAULT uuid(), name varchar(255) NOT NULL, role varchar(50) DEFAULT 'player',
  teamID char(36), created_at datetime DEFAULT current_timestamp(), updated_at datetime DEFAULT current_timestamp(),
  password varchar(255), PRIMARY KEY (id));
CREATE TABLE IF NOT EXISTS Participant (userID char(36) NOT NULL, eventID char(36) NOT NULL,
  joined_at datetime DEFAULT current_timestamp(), teamID uuid, PRIMARY KEY (userID, eventID));
"""


def sql(statement, args=None):
  c = get_db()
  try:
    with c.cursor() as cur:
      cur.execute(statement, args)
      rows = cur.fetchall()
    c.commit()
    return rows
  finally:
    c.close()


def run_script(text):
  for stmt in [s.strip() for s in text.split(';')]:
    lines = [ln for ln in stmt.splitlines() if not ln.strip().startswith('--')]
    if '\n'.join(lines).strip():
      sql('\n'.join(lines))


@pytest.fixture(scope='session')
def app():
  run_script(SCHEMA)
  with open(os.path.join(HERE, '..', '..', 'migrations', '0003_event_payments.sql')) as f:
    migration = f.read()
  run_script(migration)
  run_script(migration)  # must be safe to run twice
  application = create_app()
  application.config['TESTING'] = True
  return application


@pytest.fixture
def world(app):
  event_id, admin_id, player_id = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
  sql("INSERT INTO Event (id, name) VALUES (%s, 'Test crawl')", [event_id])
  sql("INSERT INTO User (id, name, role) VALUES (%s, 'org', 'ADMIN'), (%s, 'pl', 'player')", [admin_id, player_id])
  return types.SimpleNamespace(event_id=event_id, admin_id=admin_id, player_id=player_id)


def client_as(app, user_id):
  c = app.test_client()
  with c.session_transaction() as s:
    s['user_id'] = user_id
  return c


def signed(payload, secret=WHSEC):
  t = int(time.time())
  sig = hmac.new(secret.encode(), f"{t}.{payload}".encode(), hashlib.sha256).hexdigest()
  return {'Stripe-Signature': f"t={t},v1={sig}", 'Content-Type': 'application/json'}


def session_event(event_id, session_id, tier='society', amount=1500, evt_id=None, paid=True,
                  type_='checkout.session.completed'):
  return json.dumps({
    'id': evt_id or f"evt_{uuid.uuid4().hex}", 'type': type_, 'object': 'event',
    'data': {'object': {'id': session_id, 'object': 'checkout.session', 'amount_total': amount, 'currency': 'gbp',
                        'payment_status': 'paid' if paid else 'unpaid', 'payment_intent': 'pi_test_1',
                        'client_reference_id': event_id, 'metadata': {'event_id': event_id, 'tier': tier}}}})


@pytest.fixture
def fake_checkout(monkeypatch):
  made = []

  def create(**kw):
    made.append(kw)
    return types.SimpleNamespace(id=f"cs_test_{uuid.uuid4().hex}", url='https://checkout.stripe.com/c/pay/cs_test_x', status='open')
  monkeypatch.setattr(pay.stripe.checkout.Session, 'create', staticmethod(create))
  return made


def test_status_before_payment(app, world):
  r = client_as(app, world.admin_id).post('/api/payments/status', json={'event_id': world.event_id})
  body = r.get_json()['received']
  assert r.status_code == 200 and body['available'] and not body['paid'] and body['free_team_limit'] == 3


def test_checkout_needs_admin(app, world, fake_checkout):
  r = client_as(app, world.player_id).post('/api/payments/checkout', json={'event_id': world.event_id, 'tier': 'group'})
  assert r.status_code == 403 and not fake_checkout


def test_checkout_creates_session_and_row(app, world, fake_checkout):
  r = client_as(app, world.admin_id).post('/api/payments/checkout', json={'event_id': world.event_id, 'tier': 'group'})
  assert r.status_code == 200 and r.get_json()['received']['url'].startswith('https://checkout.stripe.com/')
  kw = fake_checkout[0]
  assert kw['mode'] == 'payment' and kw['line_items'][0]['price_data']['unit_amount'] == 999
  assert kw['line_items'][0]['price_data']['currency'] == 'gbp' and kw['metadata']['event_id'] == world.event_id
  assert kw['success_url'] == f"https://crawl.example.test/event-details/{world.event_id}?paid=1"
  rows = sql("SELECT tier, status, amount_total FROM EventPayment WHERE event_id = %s", [world.event_id])
  assert rows == [{'tier': 'group', 'status': 'open', 'amount_total': 999}]


def test_bad_tier_rejected(app, world, fake_checkout):
  r = client_as(app, world.admin_id).post('/api/payments/checkout', json={'event_id': world.event_id, 'tier': 'free-lol'})
  assert r.status_code == 400


def test_webhook_rejects_bad_signature(app, world):
  payload = session_event(world.event_id, 'cs_test_bad')
  r = app.test_client().post('/api/stripe/webhook', data=payload, headers=signed(payload, 'whsec_wrong'))
  assert r.status_code == 400
  assert sql("SELECT paid_at FROM Event WHERE id = %s", [world.event_id])[0]['paid_at'] is None


def test_webhook_marks_paid_once(app, world):
  payload = session_event(world.event_id, 'cs_test_paid_1', evt_id='evt_same_1')
  c = app.test_client()
  r1 = c.post('/api/stripe/webhook', data=payload, headers=signed(payload))
  r2 = c.post('/api/stripe/webhook', data=payload, headers=signed(payload))
  assert r1.get_json()['received'] == 'paid' and r2.get_json()['received'] == 'duplicate'
  ev = sql("SELECT paid_at, paid_tier FROM Event WHERE id = %s", [world.event_id])[0]
  assert ev['paid_at'] is not None and ev['paid_tier'] == 'society'
  assert sql("SELECT COUNT(*) n FROM EventPayment WHERE event_id = %s AND status = 'paid'", [world.event_id])[0]['n'] == 1
  r = client_as(app, world.admin_id).post('/api/payments/checkout', json={'event_id': world.event_id, 'tier': 'group'})
  assert r.status_code == 409


def test_webhook_updates_open_row(app, world, fake_checkout):
  client_as(app, world.admin_id).post('/api/payments/checkout', json={'event_id': world.event_id, 'tier': 'group'})
  sid = sql("SELECT stripe_session_id s FROM EventPayment WHERE event_id = %s", [world.event_id])[0]['s']
  payload = session_event(world.event_id, sid, tier='group', amount=999)
  assert app.test_client().post('/api/stripe/webhook', data=payload, headers=signed(payload)).get_json()['received'] == 'paid'
  assert sql("SELECT status FROM EventPayment WHERE stripe_session_id = %s", [sid])[0]['status'] == 'paid'


def test_webhook_ignores_wrong_amount_and_unpaid(app, world):
  c = app.test_client()
  p1 = session_event(world.event_id, 'cs_test_cheap', amount=1)
  p2 = session_event(world.event_id, 'cs_test_unpaid', paid=False)
  assert c.post('/api/stripe/webhook', data=p1, headers=signed(p1)).get_json()['received'].startswith('ignored')
  assert c.post('/api/stripe/webhook', data=p2, headers=signed(p2)).get_json()['received'] == 'ignored'
  assert sql("SELECT paid_at FROM Event WHERE id = %s", [world.event_id])[0]['paid_at'] is None


def test_team_limit_only_when_enforced(app, world, monkeypatch):
  for n in range(3):
    sql("INSERT INTO Team (id, name, eventID) VALUES (%s, %s, %s)", [str(uuid.uuid4()), f"t{n}", world.event_id])
  assert pay.team_limit_reached(world.event_id) is False
  monkeypatch.setenv('PAYMENTS_ENFORCE', '1')
  assert pay.team_limit_reached(world.event_id) is True
  r = client_as(app, world.admin_id).post('/api/save-new-team', json={'name': 'x', 'colour': '#000', 'event_id': world.event_id})
  assert r.status_code == 402
  sql("UPDATE Event SET paid_at = NOW(), paid_tier = 'group' WHERE id = %s", [world.event_id])
  assert pay.team_limit_reached(world.event_id) is False


def test_live_key_refused(app, world, monkeypatch):
  monkeypatch.setenv('STRIPE_SECRET_KEY', 'sk_live_nope')
  r = client_as(app, world.admin_id).post('/api/payments/status', json={'event_id': world.event_id})
  assert r.get_json()['received']['available'] is False
  r = client_as(app, world.admin_id).post('/api/payments/checkout', json={'event_id': world.event_id, 'tier': 'group'})
  assert r.status_code == 503


def test_second_click_reuses_open_session(app, world, fake_checkout, monkeypatch):
  c = client_as(app, world.admin_id)
  c.post("/api/payments/checkout", json={"event_id": world.event_id, "tier": "society"})
  monkeypatch.setattr(pay.stripe.checkout.Session, "retrieve",
                      staticmethod(lambda sid: types.SimpleNamespace(id=sid, status="open", url="https://checkout.stripe.com/c/pay/reused")))
  r = c.post("/api/payments/checkout", json={"event_id": world.event_id, "tier": "society"})
  assert r.get_json()["received"]["url"].endswith("/reused") and len(fake_checkout) == 1

  def boom(sid):
    raise pay.stripe.StripeError("gone")
  monkeypatch.setattr(pay.stripe.checkout.Session, "retrieve", staticmethod(boom))
  r = c.post("/api/payments/checkout", json={"event_id": world.event_id, "tier": "society"})
  assert r.status_code == 200 and len(fake_checkout) == 2
