"""Free-access codes: Tamair hands a friend a code; their organiser types it on Crawl Setup and the
crawl is unlocked exactly as if paid (Event.paid_at, paid_tier='code', unlocked_by_code).

Codes have a max number of uses and an optional expiry, can be switched off, and every use is logged
(AccessCodeUse). The super-admin page /admin-codes lists them with usage.
Schema: migrations/0009_access_codes.sql.
"""
import secrets
import uuid

from flask import Blueprint, request, session, jsonify

from .SQL_manager import get_db, _close_conn, _run
from .organisers import event_manager_required
from .security import login_blocked, record_login, too_many_tries, client_ip

access_codes = Blueprint('access_codes', __name__)
ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'  # no 0/O/1/I to read out in a noisy pub


def _norm(code):
  return ''.join(ch for ch in str(code or '').upper() if ch.isalnum())[:40]


def new_code(prefix=''):
  body = ''.join(secrets.choice(ALPHABET) for _ in range(8))
  p = _norm(prefix)[:8]
  return f"{p}{body}" if p else body


def _owner():
  from .routes import is_owner
  return is_owner()


@access_codes.route('/api/redeem-access-code', methods=['POST'])
@event_manager_required
def redeem():
  data = request.get_json(silent=True) or {}
  event_id = data.get('event_id')
  code = _norm(data.get('code'))
  throttle = 'code:' + client_ip()
  if login_blocked(throttle, 10):
    return too_many_tries()
  if not code:
    return jsonify({"status": "failed", "received": "Type the code"}), 400

  conn = None
  try:
    conn = get_db()
    conn.begin()
    with conn.cursor() as cur:
      cur.execute("SELECT paid_at FROM Event WHERE id = %s AND deleted_at IS NULL FOR UPDATE", [event_id])
      ev = cur.fetchone()
      if not ev:
        conn.rollback()
        return jsonify({"status": "failed", "received": "Crawl not found"}), 404
      if ev['paid_at']:
        conn.rollback()
        return jsonify({"status": "success", "received": "Already unlocked"})
      cur.execute(
        "SELECT id FROM AccessCode WHERE code = %s AND active = 1 AND uses < max_uses "
        "AND (expires_at IS NULL OR expires_at > NOW()) FOR UPDATE", [code])
      row = cur.fetchone()
      if not row:
        conn.rollback()
        record_login(throttle, False)
        return jsonify({"status": "failed", "received": "That code doesn't work (wrong, used up or expired)."}), 400
      cur.execute("UPDATE AccessCode SET uses = uses + 1 WHERE id = %s", [row['id']])
      cur.execute("INSERT INTO AccessCodeUse (id, code_id, event_id, user_id) VALUES (%s, %s, %s, %s)",
                  [str(uuid.uuid4()), row['id'], event_id, session.get('user_id')])
      cur.execute("UPDATE Event SET paid_at = NOW(), paid_tier = 'code', unlocked_by_code = %s WHERE id = %s",
                  [row['id'], event_id])
    conn.commit()
  except Exception as e:
    if conn:
      try:
        conn.rollback()
      except Exception:
        pass
    print(f"redeem code failed: {e}")
    return jsonify({"status": "failed", "received": "Could not use that code. Try again."}), 500
  finally:
    _close_conn(conn)
  return jsonify({"status": "success", "received": "Unlocked"})


# ---- super-admin (OWNER) ----

@access_codes.route('/api/access-codes', methods=['POST'])
def list_codes():
  if not _owner():
    return jsonify({"status": "failed", "received": "Forbidden"}), 403
  codes = _run(
    "SELECT id, code, label, max_uses, uses, expires_at, active, created_at, "
    "(expires_at IS NOT NULL AND expires_at <= NOW()) AS expired FROM AccessCode ORDER BY created_at DESC", []) or []
  uses = _run(
    "SELECT cu.code_id, cu.used_at, e.name AS event_name, e.id AS event_id, u.name AS user_name "
    "FROM AccessCodeUse cu JOIN Event e ON e.id = cu.event_id LEFT JOIN User u ON u.id = cu.user_id "
    "ORDER BY cu.used_at DESC", []) or []
  by_code = {}
  for u in uses:
    by_code.setdefault(u['code_id'], []).append(u)
  for c in codes:
    c['used_by'] = by_code.get(c['id'], [])
  return jsonify({"status": "success", "received": codes})


@access_codes.route('/api/create-access-code', methods=['POST'])
def create_code():
  if not _owner():
    return jsonify({"status": "failed", "received": "Forbidden"}), 403
  data = request.get_json(silent=True) or {}
  label = ' '.join(str(data.get('label') or '').split())[:120]
  try:
    max_uses = max(1, min(1000, int(data.get('max_uses') or 1)))
    days = int(data['expires_days']) if data.get('expires_days') not in (None, '', 0, '0') else None
  except (TypeError, ValueError):
    return jsonify({"status": "failed", "received": "Max uses and expiry must be numbers"}), 400
  code = _norm(data.get('code')) or new_code(label.split(' ')[0] if label else '')
  if len(code) < 6:
    return jsonify({"status": "failed", "received": "Codes need at least 6 letters/numbers"}), 400
  try:
    _run("INSERT INTO AccessCode (id, code, label, max_uses, expires_at, created_by) VALUES "
         "(%s, %s, %s, %s, " + ("NOW() + INTERVAL %s DAY" if days else "%s") + ", %s)",
         [str(uuid.uuid4()), code, label, max_uses, days, session.get('user_id')])
  except Exception:
    return jsonify({"status": "failed", "received": "That code already exists"}), 409
  return jsonify({"status": "success", "received": code})


@access_codes.route('/api/set-access-code-active', methods=['POST'])
def set_code_active():
  if not _owner():
    return jsonify({"status": "failed", "received": "Forbidden"}), 403
  data = request.get_json(silent=True) or {}
  _run("UPDATE AccessCode SET active = %s WHERE id = %s", [1 if data.get('active') else 0, data.get('id')])
  return jsonify({"status": "success", "received": bool(data.get('active'))})
