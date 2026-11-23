"""Join a crawl from a QR code / link, as a guest (just a name) or with your account.

- Event.join_token: unguessable (secrets.token_urlsafe), made on first use, regenerable by the organiser.
  Regenerating kills the old link and QR code.
- Event.max_players: player cap (NULL = DEFAULT_MAX_PLAYERS).
- Guests are User rows with role 'guest' and no password. They're logged in by their session cookie only,
  so they never need an account. Guest names don't block anyone signing up with that name.

Schema: migrations/0006_join_links.sql.
"""
import io
import os
import secrets
import uuid

from flask import Blueprint, request, session, jsonify, Response

from .SQL_manager import _run
from .organisers import event_manager_required, can_change_refs
from .security import login_blocked, record_login, too_many_tries, client_ip

join = Blueprint('join', __name__)

DEFAULT_MAX_PLAYERS = 60
HARD_MAX_PLAYERS = 300
MAX_JOINS_PER_IP = 80  # a whole society can be on one wifi


def public_base_url():
  return (os.getenv('PUBLIC_BASE_URL') or request.host_url).rstrip('/')


def _event_by_token(token):
  if not token or len(token) > 64:
    return None
  rows = _run("SELECT id, name, max_players, locked FROM Event WHERE join_token = %s AND deleted_at IS NULL LIMIT 1",
              [token])
  return rows[0] if rows else None


def _ensure_token(event_id, regenerate=False):
  rows = _run("SELECT join_token FROM Event WHERE id = %s", [event_id])
  if not rows:
    return None
  if rows[0].get('join_token') and not regenerate:
    return rows[0]['join_token']
  token = secrets.token_urlsafe(16)
  _run("UPDATE Event SET join_token = %s WHERE id = %s", [token, event_id])
  return token


def _player_count(event_id):
  rows = _run("SELECT COUNT(*) AS n FROM Participant WHERE eventID = %s", [event_id])
  return int(rows[0]['n']) if rows else 0


def _cap(ev):
  return int(ev.get('max_players') or DEFAULT_MAX_PLAYERS)


def _teams(event_id):
  return _run(
    "SELECT t.id, t.name, t.colour, COUNT(p.userID) AS players FROM Team t "
    "LEFT JOIN Participant p ON p.teamID = t.id AND p.eventID = t.eventID "
    "WHERE t.eventID = %s GROUP BY t.id, t.name, t.colour ORDER BY t.created_at", [event_id]) or []


def _join_url(token):
  return f"{public_base_url()}/join/{token}"


# ---- organiser side ----

@join.route('/api/join-info', methods=['POST'])
@event_manager_required
def join_info():
  data = request.get_json(silent=True) or {}
  event_id = data.get('event_id')
  token = _ensure_token(event_id)
  if not token:
    return jsonify({"status": "failed", "received": "Event not found"}), 404
  ev = _run("SELECT max_players FROM Event WHERE id = %s", [event_id])[0]
  return jsonify({"status": "success", "received": {
    "url": _join_url(token), "token": token, "players": _player_count(event_id),
    "max_players": _cap(ev), "hard_max": HARD_MAX_PLAYERS}})


@join.route('/api/regenerate-join-link', methods=['POST'])
@event_manager_required
def regenerate_join_link():
  event_id = (request.get_json(silent=True) or {}).get('event_id')
  if not can_change_refs(event_id):
    return jsonify({"status": "failed", "received": "Only the organiser can make a new link"}), 403
  token = _ensure_token(event_id, regenerate=True)
  return jsonify({"status": "success", "received": {"url": _join_url(token), "token": token}})


@join.route('/api/set-player-cap', methods=['POST'])
@event_manager_required
def set_player_cap():
  data = request.get_json(silent=True) or {}
  try:
    cap = int(data.get('max_players'))
  except (TypeError, ValueError):
    return jsonify({"status": "failed", "received": "Enter a number"}), 400
  if cap < 1 or cap > HARD_MAX_PLAYERS:
    return jsonify({"status": "failed", "received": f"Pick between 1 and {HARD_MAX_PLAYERS}"}), 400
  _run("UPDATE Event SET max_players = %s WHERE id = %s", [cap, data.get('event_id')])
  return jsonify({"status": "success", "received": cap})


@join.route('/api/join-qr.svg', methods=['GET'])
@event_manager_required
def join_qr():
  import segno
  event_id = request.args.get('event_id')
  token = _ensure_token(event_id)
  if not token:
    return Response("not found", status=404)
  buf = io.BytesIO()
  segno.make(_join_url(token), error='m').save(buf, kind='svg', scale=10, border=2, dark='#111827', light='#ffffff',
                                               xmldecl=False, svgns=True)
  resp = Response(buf.getvalue(), mimetype='image/svg+xml')
  resp.headers['Cache-Control'] = 'no-store'
  return resp


# ---- player side ----

@join.route('/api/join-preview', methods=['POST'])
def join_preview():
  token = str((request.get_json(silent=True) or {}).get('token') or '')
  ev = _event_by_token(token)
  if not ev:
    return jsonify({"status": "failed", "received": "This invite link doesn't work any more. Ask your organiser for the new QR code."}), 404
  count = _player_count(ev['id'])
  already = False
  if session.get('user_id'):
    rows = _run("SELECT 1 FROM Participant WHERE eventID = %s AND userID = %s", [ev['id'], session['user_id']])
    already = bool(rows)
  return jsonify({"status": "success", "received": {
    "event_id": ev['id'], "name": ev['name'], "teams": _teams(ev['id']),
    "players": count, "full": count >= _cap(ev), "already_joined": already,
    "logged_in": bool(session.get('user_id'))}})


@join.route('/api/join', methods=['POST'])
def join_crawl():
  data = request.get_json(silent=True) or {}
  ev = _event_by_token(str(data.get('token') or ''))
  if not ev:
    return jsonify({"status": "failed", "received": "This invite link doesn't work any more. Ask your organiser for the new QR code."}), 404
  event_id = ev['id']

  user_id = session.get('user_id')
  if user_id:
    rows = _run("SELECT id, name, role FROM User WHERE id = %s", [user_id])
    user = rows[0] if rows else None
    if not user:
      session.clear()
      user_id = None
  if user_id and _run("SELECT 1 FROM Participant WHERE eventID = %s AND userID = %s", [event_id, user_id]):
    return jsonify({"status": "success", "received": {"event_id": event_id, "profile": user}})

  if _player_count(event_id) >= _cap(ev):
    return jsonify({"status": "failed", "received": "This crawl is full. Ask your organiser to raise the player limit."}), 409

  if not user_id:
    name = ' '.join(str(data.get('name') or '').split())[:40]
    if len(name) < 1:
      return jsonify({"status": "failed", "received": "Type your name"}), 400
    if login_blocked('join:' + client_ip(), MAX_JOINS_PER_IP):
      return too_many_tries()
    record_login('join:' + client_ip(), False)
    user_id = str(uuid.uuid4())
    _run("INSERT INTO User (id, name, role, password) VALUES (%s, %s, 'guest', NULL)", [user_id, name])
    user = {"id": user_id, "name": name, "role": "guest"}
    session.clear()
    session.permanent = True
    session['user_id'] = user_id
    session['role'] = 'guest'

  teams = _teams(event_id)
  team_id = data.get('team_id')
  if team_id not in {t['id'] for t in teams}:
    team_id = min(teams, key=lambda t: t['players'])['id'] if teams else None
  _run("INSERT IGNORE INTO Participant (userID, eventID, teamID) VALUES (%s, %s, %s)", [user_id, event_id, team_id])
  return jsonify({"status": "success", "received": {"event_id": event_id, "profile": user}})
