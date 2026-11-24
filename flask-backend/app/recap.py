"""End-of-crawl recap: final standings, top players, award winners, pubs, numbers.
The frontend (/recap/:id) also draws the shareable winners poster from this data.
"""
from flask import Blueprint, request, jsonify

from .SQL_manager import _run

recap = Blueprint('recap', __name__)


def build_recap(event_id):
  ev = (_run("SELECT id, name, created_at, awards_results_visible, features FROM Event WHERE id = %s AND deleted_at IS NULL",
             [event_id]) or [None])[0]
  if not ev:
    return None
  players = _run(
    "SELECT u.id, u.name, p.teamID AS team_id, COALESCE(SUM(pt.point_number), 0) AS points "
    "FROM Participant p JOIN User u ON u.id = p.userID "
    "LEFT JOIN Point pt ON pt.userID = p.userID AND pt.eventID = p.eventID "
    "WHERE p.eventID = %s GROUP BY u.id, u.name, p.teamID", [event_id]) or []
  teams = _run(
    "SELECT t.id, t.name, t.colour, "
    "  (SELECT COALESCE(SUM(tp.point_number), 0) FROM TeamPoint tp WHERE tp.team_id = t.id AND tp.event_id = t.eventID) AS adjustment "
    "FROM Team t WHERE t.eventID = %s", [event_id]) or []
  for t in teams:
    members = [p for p in players if p['team_id'] == t['id']]
    t['members'] = sorted([{"name": m['name'], "points": int(m['points'])} for m in members], key=lambda m: -m['points'])
    t['points'] = sum(m['points'] for m in t['members']) + int(t['adjustment'] or 0)
    t['adjustment'] = int(t['adjustment'] or 0)
  teams.sort(key=lambda t: -t['points'])
  top_players = sorted(({"name": p['name'], "points": int(p['points']),
                         "team": next((t['name'] for t in teams if t['id'] == p['team_id']), None)} for p in players),
                       key=lambda p: -p['points'])[:5]
  pubs = _run("SELECT name FROM Pub WHERE eventID = %s ORDER BY order_index", [event_id]) or []
  photos = (_run("SELECT COUNT(*) AS n FROM Photo WHERE event_id = %s", [event_id]) or [{'n': 0}])[0]['n']

  awards = []
  for a in _run("SELECT id, name, target_type FROM EventAward WHERE event_id = %s ORDER BY sort_order", [event_id]) or []:
    votes = _run("SELECT nominee_id, nominee_type, COUNT(*) AS n FROM EventAwardVote WHERE award_id = %s "
                 "GROUP BY nominee_id, nominee_type ORDER BY n DESC LIMIT 1", [a['id']]) or []
    winner = None
    if votes:
      v = votes[0]
      if v['nominee_type'] == 'team':
        winner = next((t['name'] for t in teams if t['id'] == v['nominee_id']), None)
      else:
        winner = next((p['name'] for p in players if p['id'] == v['nominee_id']), None)
      winner = {"name": winner or '?', "votes": int(v['n'])}
    awards.append({"name": a['name'], "winner": winner})

  return {
    "event": {"id": ev['id'], "name": ev['name'], "date": ev['created_at'].isoformat() if ev['created_at'] else None},
    "teams": [{k: t[k] for k in ('name', 'colour', 'points', 'adjustment', 'members')} for t in teams],
    "top_players": top_players,
    "awards": awards,
    "awards_visible": bool(ev['awards_results_visible']),
    "pubs": [p['name'] for p in pubs],
    "stats": {"players": len(players), "points": sum(int(p['points']) for p in players), "photos": int(photos),
              "pubs": len(pubs)},
  }


@recap.route('/api/recap', methods=['POST'])
def get_recap():
  from .routes import can_view_event, can_manage_event
  event_id = (request.get_json(silent=True) or {}).get('event_id')
  if not event_id or not can_view_event(event_id):
    return jsonify({"status": "failed", "received": "Forbidden"}), 403
  out = build_recap(event_id)
  if not out:
    return jsonify({"status": "failed", "received": "Crawl not found"}), 404
  # Award winners stay secret until the ref shows results (the ref/organiser can always see them)
  if not out['awards_visible'] and not can_manage_event(event_id):
    out['awards'] = [{"name": a['name'], "winner": None} for a in out['awards']]
  return jsonify({"status": "success", "received": out})
