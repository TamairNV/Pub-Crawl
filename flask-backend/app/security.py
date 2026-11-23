"""Passwords, login throttling and cross-site request checks.

Passwords: stored as werkzeug hashes (scrypt). Old rows still hold the plain passkey; those are
accepted once and upgraded to a hash on that successful login (see verify_and_upgrade).

Throttling: failed logins are counted in the LoginAttempt table (migrations/0004_login_throttle.sql),
so the limit holds across gunicorn workers. If the table is missing, throttling is skipped.

CSRF: the session cookie is SameSite=Lax, and every state-changing /api request from a browser must
come from our own origin (Origin, or Sec-Fetch-Site when Origin is absent). Requests without either
header are not from a browser, so they carry no victim cookie.
"""
import hmac
import os
import secrets
from urllib.parse import urlsplit

from flask import request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

from .SQL_manager import _run

HASH_PREFIXES = ('scrypt:', 'pbkdf2:')
FAIL_WINDOW_MIN = 15
MAX_FAILS_PER_NAME = 8
MAX_FAILS_PER_IP = 30
MAX_SIGNUPS_PER_IP = 40  # a whole group often shares one pub wifi IP
CSRF_EXEMPT = ('/api/stripe/webhook',)
UNSAFE_METHODS = ('POST', 'PUT', 'PATCH', 'DELETE')


def hash_password(raw):
  return generate_password_hash(str(raw), method='scrypt')


def is_hashed(stored):
  return isinstance(stored, str) and stored.startswith(HASH_PREFIXES)


def verify_and_upgrade(user_row, given):
  """True if `given` matches. Upgrades a legacy plain-text password to a hash on success."""
  stored = user_row.get('password')
  if stored is None or given is None:
    return False
  given = str(given)
  if is_hashed(stored):
    return check_password_hash(stored, given)
  if hmac.compare_digest(str(stored).encode(), given.encode()):
    try:
      _run("UPDATE User SET password = %s WHERE id = %s", [hash_password(given), user_row['id']])
    except Exception as e:
      print(f"Password upgrade failed for {user_row.get('id')}: {e}")
    return True
  return False


def new_passkey():
  """Short, easy-to-type passkey a ref can read out to a player."""
  return f"{secrets.randbelow(10**6):06d}"


# ---- login throttling ----

def client_ip():
  return (request.remote_addr or '')[:64]


def login_blocked(name, max_per_name=MAX_FAILS_PER_NAME):
  try:
    rows = _run(
      "SELECT "
      " SUM(name = %s) AS by_name, SUM(ip = %s AND name NOT LIKE 'create:%%') AS by_ip "
      "FROM LoginAttempt WHERE success = 0 AND created_at > NOW() - INTERVAL %s MINUTE "
      "AND (name = %s OR ip = %s)",
      [name, client_ip(), FAIL_WINDOW_MIN, name, client_ip()])
  except Exception:
    return False
  r = rows[0] if rows else {}
  return int(r.get('by_name') or 0) >= max_per_name or int(r.get('by_ip') or 0) >= MAX_FAILS_PER_IP


def record_login(name, success):
  try:
    _run("INSERT INTO LoginAttempt (ip, name, success) VALUES (%s, %s, %s)",
         [client_ip(), str(name)[:255], 1 if success else 0])
    if success:
      _run("DELETE FROM LoginAttempt WHERE name = %s AND success = 0", [str(name)[:255]])
    elif secrets.randbelow(50) == 0:
      _run("DELETE FROM LoginAttempt WHERE created_at < NOW() - INTERVAL 1 DAY", [])
  except Exception:
    pass


def too_many_tries():
  return jsonify({"status": "failed", "received": "Too many tries. Wait a few minutes and try again."}), 429


# ---- cross-site request check ----

def _allowed_origins():
  out = {f"{request.scheme}://{request.host}"}
  base = os.getenv('PUBLIC_BASE_URL', '').strip()
  if base:
    p = urlsplit(base)
    out.add(f"{p.scheme}://{p.netloc}")
  out.add("http://localhost:4200")  # ng serve
  return out


def csrf_check():
  """before_request hook. Returns a 403 response for cross-site state-changing API calls."""
  if request.method not in UNSAFE_METHODS or not request.path.startswith('/api/'):
    return None
  if request.path.startswith(CSRF_EXEMPT):
    return None
  origin = request.headers.get('Origin')
  if origin:
    if origin.rstrip('/') in _allowed_origins():
      return None
  else:
    site = request.headers.get('Sec-Fetch-Site')
    if site in (None, 'same-origin', 'none'):
      return None
  return jsonify({"status": "failed", "received": "Cross-site request blocked"}), 403
