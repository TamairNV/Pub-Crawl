"""End-to-end Stripe test driver (run inside scripts/e2e-stripe.sh, against a THROWAWAY DB only).

  setup  create the minimal schema + payments migration in the throwaway DB
  run    log in as a throwaway admin, create a test crawl, start a real test-mode Checkout,
         wait for it to be paid (4242 card in a browser), then replay the same Stripe event
         with a valid signature and check it is a no-op.
"""
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.request
import uuid

import pymysql
import stripe

OUT = '/e2e/out'
APP = 'http://127.0.0.1:8001'
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


def db():
  return pymysql.connect(host=os.environ['DB_HOST'], user=os.environ['DB_USER'], password=os.environ['DB_PASSWORD'],
                         database=os.environ['DB_NAME'], port=int(os.environ['DB_PORT']),
                         cursorclass=pymysql.cursors.DictCursor, autocommit=True)


def sql(q, args=None):
  c = db()
  try:
    with c.cursor() as cur:
      cur.execute(q, args)
      return cur.fetchall()
  finally:
    c.close()


def run_script(text):
  for stmt in text.split(';'):
    body = '\n'.join(ln for ln in stmt.splitlines() if not ln.strip().startswith('--')).strip()
    if body:
      sql(body)


def post(path, body, cookie=None, raw=None, headers=None):
  data = raw if raw is not None else json.dumps(body).encode()
  h = {'Content-Type': 'application/json'}
  if cookie:
    h['Cookie'] = cookie
  h.update(headers or {})
  req = urllib.request.Request(APP + path, data=data, headers=h, method='POST')
  try:
    with urllib.request.urlopen(req, timeout=30) as r:
      return r.status, json.loads(r.read() or b'{}'), r.headers.get_all('Set-Cookie') or []
  except urllib.error.HTTPError as e:
    return e.code, json.loads(e.read() or b'{}'), []


def say(msg):
  print(f"[e2e] {msg}", flush=True)
  with open(f"{OUT}/result.txt", 'a') as f:
    f.write(msg + '\n')


def setup():
  run_script(SCHEMA)
  run_script(open('/work/migrations/20261123_event_payments.sql').read())
  say('schema + payments migration loaded into the throwaway DB')


def run():
  admin_pw = uuid.uuid4().hex  # throwaway DB only
  event_id = str(uuid.uuid4())
  sql("INSERT INTO User (id, name, role, password) VALUES (%s, 'e2e-organiser', 'ADMIN', %s)", [str(uuid.uuid4()), admin_pw])
  sql("INSERT INTO Event (id, name) VALUES (%s, 'E2E test crawl')", [event_id])
  for n in range(3):
    sql("INSERT INTO Team (id, name, eventID) VALUES (%s, %s, %s)", [str(uuid.uuid4()), f"Team {n + 1}", event_id])

  status, body, cookies = post('/api/login-user', {'name': 'e2e-organiser', 'passkey': admin_pw})
  assert status == 200 and body.get('status') == 'success', (status, body)
  cookie = '; '.join(c.split(';', 1)[0] for c in cookies)

  status, body, _ = post('/api/payments/status', {'event_id': event_id}, cookie)
  say(f"status before: http {status}, available={body['received'].get('available')}, paid={body['received'].get('paid')}")
  assert body['received'].get('available') is True, 'payments not available: test key missing or not sk_test_'

  status, body, _ = post('/api/payments/checkout', {'event_id': event_id, 'tier': 'group'}, cookie)
  assert status == 200, (status, body)
  url = body['received']['url']
  with open(f"{OUT}/checkout_url.txt", 'w') as f:
    f.write(url + '\n')
  say('checkout session created (Group, 9.99 GBP); URL in out/checkout_url.txt: pay it with the 4242 test card')

  deadline = time.time() + 15 * 60
  while time.time() < deadline:
    row = sql("SELECT paid_at, paid_tier FROM Event WHERE id = %s", [event_id])[0]
    if row['paid_at']:
      break
    time.sleep(3)
  else:
    say('TIMEOUT: event was not marked paid within 15 minutes')
    sys.exit(1)
  say(f"event marked paid: tier={row['paid_tier']}")

  pays = sql("SELECT status, amount_total, currency, stripe_payment_intent IS NOT NULL AS has_pi FROM EventPayment WHERE event_id = %s", [event_id])
  evts = sql("SELECT id, type FROM StripeWebhookEvent")
  say(f"EventPayment rows: {pays}")
  say(f"webhook events recorded: {[e['type'] for e in evts]}")

  # Replay the real Stripe event, signed with the same secret: must be a no-op.
  stripe.api_key = os.environ['STRIPE_SECRET_KEY']
  paid_evt = next(e for e in evts if e['type'] == 'checkout.session.completed')
  payload = json.dumps(stripe.Event.retrieve(paid_evt['id']).to_dict_recursive() if hasattr(stripe.Event, 'to_dict_recursive') else stripe.Event.retrieve(paid_evt['id']).to_dict())
  t = int(time.time())
  sig = hmac.new(os.environ['STRIPE_WEBHOOK_SECRET'].encode(), f"{t}.{payload}".encode(), hashlib.sha256).hexdigest()
  status, body, _ = post('/api/stripe/webhook', None, raw=payload.encode(), headers={'Stripe-Signature': f"t={t},v1={sig}"})
  say(f"replay of {paid_evt['id']}: http {status}, result={body.get('received')}")
  n_paid = sql("SELECT COUNT(*) n FROM EventPayment WHERE event_id = %s AND status = 'paid'", [event_id])[0]['n']
  say(f"paid EventPayment rows after replay: {n_paid}")
  assert body.get('received') == 'duplicate' and n_paid == 1

  status, body, _ = post('/api/payments/checkout', {'event_id': event_id, 'tier': 'society'}, cookie)
  say(f"second checkout after paying: http {status} ({body.get('received')})")
  assert status == 409
  with open(f"{OUT}/event_id.txt", 'w') as f:
    f.write(event_id + '\n')
  say('E2E PASS')


if __name__ == '__main__':
  {'setup': setup, 'run': run}[sys.argv[1]]()
