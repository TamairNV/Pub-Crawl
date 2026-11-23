"""Who may run which crawl.

- Staff: role OWNER (Tamair, super-admin) or ADMIN (legacy global admins). They can manage every crawl.
- Organiser: the user who created the crawl (Event.owner_user_id). Can manage it and add co-refs.
- Co-ref: a user listed in EventRef for that crawl. Can run and edit the crawl, but not change its refs.

Schema: migrations/0005_event_owners.sql.
"""
from functools import wraps

from flask import request, session, jsonify

from .SQL_manager import _run

STAFF_ROLES = ('admin', 'owner')
MAX_ACTIVE_CRAWLS_PER_ORGANISER = 20


def _role():
  if 'user_id' not in session:
    return ''
  try:
    out = _run("SELECT role FROM User WHERE id = %s LIMIT 1", [session['user_id']])
  except Exception:
    out = None
  role = out[0]['role'] if out else session.get('role', '')
  return str(role or '').lower()


def is_staff():
  return _role() in STAFF_ROLES


def event_access(event_id, user_id=None):
  """'staff', 'organiser', 'ref' or None for the current user and this event."""
  user_id = user_id or session.get('user_id')
  if not user_id or not event_id:
    return None
  if is_staff():
    return 'staff'
  try:
    rows = _run(
      "SELECT e.owner_user_id, "
      "  EXISTS(SELECT 1 FROM EventRef r WHERE r.event_id = e.id AND r.user_id = %s) AS is_ref "
      "FROM Event e WHERE e.id = %s AND e.deleted_at IS NULL LIMIT 1", [user_id, event_id])
  except Exception as e:
    print(f"event_access failed: {e}")
    return None
  if not rows:
    return None
  if rows[0].get('owner_user_id') == user_id:
    return 'organiser'
  if rows[0].get('is_ref'):
    return 'ref'
  return None


def can_manage_event(event_id):
  return event_access(event_id) is not None


def can_change_refs(event_id):
  return event_access(event_id) in ('staff', 'organiser')


def _event_ids_from_request():
  data = request.get_json(silent=True)
  if isinstance(data, list):  # e.g. save-people-to-event sends a list of {eventId, userId, teamId}
    return {str(p.get('eventId') or p.get('event_id') or '') for p in data if isinstance(p, dict)}
  data = data or {}
  eid = data.get('event_id') or data.get('eventId') or request.args.get('event_id')
  if eid:
    return {str(eid)}
  # Objects that belong to one crawl, for endpoints that only send the object's id
  lookups = (
    ('rule_id', "SELECT COALESCE(r.event_id, p.eventID) AS eid FROM Rule r LEFT JOIN Pub p ON p.id = r.pubID WHERE r.id = %s"),
    ('pub_id', "SELECT eventID AS eid FROM Pub WHERE id = %s"),
    ('team_id', "SELECT eventID AS eid FROM Team WHERE id = %s"),
  )
  for key, sql in lookups:
    if data.get(key):
      try:
        rows = _run(sql, [data[key]])
      except Exception:
        rows = None
      return {str(rows[0]['eid'])} if rows and rows[0].get('eid') else {''}
  return {''}


def event_manager_required(f):
  """Logged in, and staff / organiser / co-ref of every crawl the request names."""
  @wraps(f)
  def wrapper(*args, **kwargs):
    if 'user_id' not in session:
      return jsonify({"status": "failed", "received": "Not logged in"}), 401
    ids = _event_ids_from_request()
    if not ids or '' in ids:
      if is_staff():
        return f(*args, **kwargs)
      return jsonify({"status": "failed", "received": "Which crawl?"}), 400
    if not all(can_manage_event(eid) for eid in ids):
      return jsonify({"status": "failed", "received": "Forbidden"}), 403
    return f(*args, **kwargs)
  return wrapper


def managed_events_sql(user_id):
  return _run(
    "SELECT DISTINCT e.*, (e.owner_user_id = %s) AS is_organiser FROM Event e "
    "LEFT JOIN EventRef r ON r.event_id = e.id AND r.user_id = %s "
    "WHERE e.deleted_at IS NULL AND (e.owner_user_id = %s OR r.user_id IS NOT NULL) "
    "ORDER BY e.created_at DESC", [user_id, user_id, user_id])


def active_crawl_count(user_id):
  rows = _run("SELECT COUNT(*) AS n FROM Event WHERE owner_user_id = %s AND deleted_at IS NULL", [user_id])
  return int(rows[0]['n']) if rows else 0


def set_event_owner_sql(event_id, user_id):
  _run("UPDATE Event SET owner_user_id = %s WHERE id = %s", [user_id, event_id])


def list_refs_sql(event_id):
  return _run(
    "SELECT u.id, u.name, 'organiser' AS kind FROM Event e JOIN User u ON u.id = e.owner_user_id WHERE e.id = %s "
    "UNION ALL "
    "SELECT u.id, u.name, 'ref' AS kind FROM EventRef r JOIN User u ON u.id = r.user_id WHERE r.event_id = %s",
    [event_id, event_id]) or []


def add_ref_sql(event_id, user_id, added_by):
  _run("INSERT IGNORE INTO EventRef (event_id, user_id, added_by) VALUES (%s, %s, %s)", [event_id, user_id, added_by])


def remove_ref_sql(event_id, user_id):
  return _run("DELETE FROM EventRef WHERE event_id = %s AND user_id = %s", [event_id, user_id])
