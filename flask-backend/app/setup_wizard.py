"""Setup wizard + rule-pack templates.

POST /api/rule-packs      the packs (any logged-in user)
POST /api/quick-setup     {event_id, teams: n | [names], pubs: [names], pack_id, wheel: bool, awards: bool}
                          fills a new crawl in one go: teams (named + coloured), pubs in order, the pack's
                          rules (whole-crawl rules + one rule per pub, cycling), and optionally the starter
                          wheel and default awards.
POST /api/apply-rule-pack {event_id, pack_id}  adds a pack's rules to an existing crawl (pubs without a rule
                          get one; whole-crawl rules are added unless one with the same name exists).
"""
from flask import Blueprint, request, jsonify

from .SQL_manager import _run, add_new_location_sql, add_new_rule_sql, create_new_team_sql, get_next_location_index_sql
from .organisers import event_manager_required

wizard = Blueprint('wizard', __name__)

TEAM_PRESETS = [
  ("Pint Pirates", "#ef4444"), ("Lager Legends", "#3b82f6"), ("Hop Squad", "#22c55e"), ("Stout Hearts", "#f59e0b"),
  ("Cider Sliders", "#a855f7"), ("Gin Genies", "#ec4899"), ("Ale Stars", "#14b8a6"), ("Shandy Bandits", "#f97316"),
]
MAX_TEAMS = 8
MAX_PUBS = 20

RULE_PACKS = [
  {
    "id": "classic",
    "name": "Classic",
    "blurb": "The standard night out. A bit silly, nobody gets hurt.",
    "general": [
      ("Wrong hand", "Drink with your left hand only. Caught using your right: -1."),
      ("No phones at the bar", "Caught on your phone while ordering: -1."),
      ("Team photo", "A team photo at every pub: +2."),
    ],
    "per_pub": [
      ("Accents only", "Everyone speaks in an accent until the next pub."),
      ("Pirate talk", "Every sentence ends in ARR. Forget: -1."),
      ("Compliment chain", "Compliment a stranger: +1 each (max 3)."),
      ("Silent round", "First drink in total silence. First to talk: -1."),
      ("Fastest round", "First team with a full round: +3."),
    ],
  },
  {
    "id": "stag-hen",
    "name": "Stag / Hen",
    "blurb": "Dares aimed at the main character. Bring the sash.",
    "general": [
      ("Guest of honour", "The stag/hen never buys their own drink. If they do: team -2."),
      ("Nickname only", "Call the stag/hen by their real name: -1."),
      ("Selfie with a stranger", "Get a stranger in a group selfie: +2."),
    ],
    "per_pub": [
      ("Toast", "Someone gives a 30-second toast to the stag/hen: +2."),
      ("Swap an item", "Swap something you're wearing with a stranger: +3."),
      ("Story time", "Tell the most embarrassing (clean) story about them: +2."),
      ("Dance floor", "Whole team dances for one song: +3."),
      ("Last orders", "Stag/hen picks the winning team for this pub: +3."),
    ],
  },
  {
    "id": "society",
    "name": "Society social",
    "blurb": "Freshers-friendly. Points for joining in, not for drinking.",
    "general": [
      ("Soft drinks count", "Any drink counts for any challenge. Nobody has to drink alcohol."),
      ("Meet someone new", "Learn a name from another team: +1 (max 3 a pub)."),
      ("Society chant", "Start your society chant in the pub: +2."),
    ],
    "per_pub": [
      ("Quiz round", "Ref asks 3 questions; +1 per right answer."),
      ("Human pyramid", "Team photo in a pyramid (safely!): +3."),
      ("Rock paper scissors", "Best of 5 against another team: winner +2."),
      ("Two truths and a lie", "Fool another team: +2."),
      ("Group selfie", "Every team in one photo: +2 each."),
    ],
  },
  {
    "id": "chill",
    "name": "Chill",
    "blurb": "No forfeits, just a scoreboard and some fun.",
    "general": [("Be nice to the staff", "Say thank you every round. Bar staff vote for a +3 bonus at the end.")],
    "per_pub": [
      ("Pub quiz", "Ref asks one question per team: +1 if right."),
      ("Best photo", "Best photo of this pub, ref decides: +2."),
    ],
  },
]
PACKS_BY_ID = {p["id"]: p for p in RULE_PACKS}


def _pack_public(p):
  return {"id": p["id"], "name": p["name"], "blurb": p["blurb"],
          "general": [{"name": n, "description": d} for n, d in p["general"]],
          "per_pub": [{"name": n, "description": d} for n, d in p["per_pub"]]}


@wizard.route('/api/rule-packs', methods=['GET', 'POST'])
def rule_packs():
  return jsonify({"status": "success", "received": [_pack_public(p) for p in RULE_PACKS]})


def _apply_pack(event_id, pack):
  existing_general = {r['name'] for r in (_run(
    "SELECT name FROM Rule WHERE event_id = %s AND pubID IS NULL", [event_id]) or [])}
  for name, desc in pack["general"]:
    if name not in existing_general:
      add_new_rule_sql(None, name, desc, event_id)
  pubs = _run(
    "SELECT p.id FROM Pub p WHERE p.eventID = %s AND NOT EXISTS (SELECT 1 FROM Rule r WHERE r.pubID = p.id) "
    "ORDER BY p.order_index", [event_id]) or []
  for i, pub in enumerate(pubs):
    name, desc = pack["per_pub"][i % len(pack["per_pub"])]
    add_new_rule_sql(pub['id'], name, desc, event_id)


@wizard.route('/api/apply-rule-pack', methods=['POST'])
@event_manager_required
def apply_rule_pack():
  data = request.get_json(silent=True) or {}
  pack = PACKS_BY_ID.get(data.get('pack_id'))
  if not pack:
    return jsonify({"status": "failed", "received": "Unknown rule pack"}), 400
  _apply_pack(data.get('event_id'), pack)
  return jsonify({"status": "success", "received": pack["id"]})


@wizard.route('/api/quick-setup', methods=['POST'])
@event_manager_required
def quick_setup():
  data = request.get_json(silent=True) or {}
  event_id = data.get('event_id')

  teams = data.get('teams') or 0
  if isinstance(teams, list):
    names = [' '.join(str(t).split())[:60] for t in teams if str(t).strip()][:MAX_TEAMS]
  else:
    try:
      n = max(0, min(MAX_TEAMS, int(teams)))
    except (TypeError, ValueError):
      n = 0
    names = [TEAM_PRESETS[i][0] for i in range(n)]
  pubs = [' '.join(str(p).split())[:120] for p in (data.get('pubs') or []) if str(p).strip()][:MAX_PUBS]
  pack = PACKS_BY_ID.get(data.get('pack_id')) if data.get('pack_id') else None

  existing_teams = int((_run("SELECT COUNT(*) AS n FROM Team WHERE eventID = %s", [event_id]) or [{'n': 0}])[0]['n'])
  if existing_teams + len(names) > MAX_TEAMS:
    names = names[:max(0, MAX_TEAMS - existing_teams)]
  from .payments import team_limit_reached, FREE_TEAM_LIMIT
  made_teams = 0
  for i, name in enumerate(names):
    if team_limit_reached(event_id):
      break
    create_new_team_sql(name, TEAM_PRESETS[(existing_teams + i) % len(TEAM_PRESETS)][1], event_id)
    made_teams += 1

  for name in pubs:
    add_new_location_sql(name, event_id, get_next_location_index_sql(event_id))

  if pack:
    _apply_pack(event_id, pack)

  if isinstance(data.get('features'), dict):
    set_features(event_id, data['features'])

  extras = []
  if data.get('wheel'):
    from .mini_events_manager import create_wheel_sql, seed_starter_wheel_items_sql
    w = create_wheel_sql(event_id, "Wheel of Fortune", "Spin for a dare")
    if w:
      seed_starter_wheel_items_sql(w['id'], event_id)
      extras.append('wheel')
  if data.get('awards'):
    from .mini_events_manager import seed_default_awards_sql
    seed_default_awards_sql(event_id)
    extras.append('awards')

  note = None
  if made_teams < len(names):
    note = f"Free crawls have up to {FREE_TEAM_LIMIT} teams. Unlock this crawl to add more."
  return jsonify({"status": "success", "received": {
    "teams": made_teams, "pubs": len(pubs), "pack": pack["id"] if pack else None, "extras": extras, "note": note}})


# ---- feature switches ----

import json
import random
import uuid as _uuid

FEATURES = ('teams', 'general_rules', 'pub_rules', 'wheel', 'awards', 'photos', 'qr_join')
# Crawls made before switches existed keep everything on
LEGACY_FEATURES = {f: True for f in FEATURES}


def get_features(event_id):
  rows = _run("SELECT features FROM Event WHERE id = %s", [event_id]) or []
  raw = rows[0].get('features') if rows else None
  out = dict(LEGACY_FEATURES)
  if raw:
    try:
      out.update({k: bool(v) for k, v in json.loads(raw).items() if k in FEATURES})
    except ValueError:
      pass
  return out


def set_features(event_id, values):
  cur = get_features(event_id)
  cur.update({k: bool(v) for k, v in (values or {}).items() if k in FEATURES})
  _run("UPDATE Event SET features = %s WHERE id = %s", [json.dumps(cur), event_id])
  return cur


@wizard.route('/api/event-features', methods=['POST'])
def event_features():
  from .routes import can_view_event
  event_id = (request.get_json(silent=True) or {}).get('event_id')
  if not event_id or not can_view_event(event_id):
    return jsonify({"status": "failed", "received": "Forbidden"}), 403
  return jsonify({"status": "success", "received": get_features(event_id)})


@wizard.route('/api/set-event-features', methods=['POST'])
@event_manager_required
def set_event_features():
  data = request.get_json(silent=True) or {}
  return jsonify({"status": "success", "received": set_features(data.get('event_id'), data.get('features'))})


# ---- teams ----

def _players(event_id):
  """Participants who play (not the organiser, co-refs or staff)."""
  return _run(
    "SELECT p.userID, p.teamID FROM Participant p JOIN User u ON u.id = p.userID JOIN Event e ON e.id = p.eventID "
    "WHERE p.eventID = %s AND (e.owner_user_id IS NULL OR p.userID <> e.owner_user_id) "
    "AND NOT EXISTS (SELECT 1 FROM EventRef r WHERE r.event_id = p.eventID AND r.user_id = p.userID) "
    "AND LOWER(COALESCE(u.role, 'player')) NOT IN ('admin', 'owner')", [event_id]) or []


@wizard.route('/api/randomise-teams', methods=['POST'])
@event_manager_required
def randomise_teams():
  """Shuffle players into even teams. only_unassigned=true keeps everyone who already has a team."""
  data = request.get_json(silent=True) or {}
  event_id = data.get('event_id')
  teams = [t['id'] for t in (_run("SELECT id FROM Team WHERE eventID = %s ORDER BY created_at", [event_id]) or [])]
  if not teams:
    return jsonify({"status": "failed", "received": "Add some teams first"}), 400
  players = _players(event_id)
  counts = {t: 0 for t in teams}
  if data.get('only_unassigned'):
    for p in players:
      if p['teamID'] in counts:
        counts[p['teamID']] += 1
    players = [p for p in players if p['teamID'] not in counts]
  random.shuffle(players)
  for p in players:
    smallest = min(counts.values())
    t = random.choice([t for t, n in counts.items() if n == smallest])
    counts[t] += 1
    _run("UPDATE Participant SET teamID = %s WHERE eventID = %s AND userID = %s", [t, event_id, p['userID']])
  return jsonify({"status": "success", "received": {"moved": len(players)}})


@wizard.route('/api/add-guest-player', methods=['POST'])
@event_manager_required
def add_guest_player():
  """A ref adds someone who isn't on the app. They can still be scored; they can join later via QR on their own phone."""
  data = request.get_json(silent=True) or {}
  event_id = data.get('event_id')
  name = ' '.join(str(data.get('name') or '').split())[:40]
  if not name:
    return jsonify({"status": "failed", "received": "Type their name"}), 400
  from .join import _player_count, _cap, _teams
  ev = (_run("SELECT id, max_players FROM Event WHERE id = %s", [event_id]) or [None])[0]
  if not ev:
    return jsonify({"status": "failed", "received": "Event not found"}), 404
  if _player_count(event_id) >= _cap(ev):
    return jsonify({"status": "failed", "received": "This crawl is full. Raise the player limit first."}), 409
  teams = _teams(event_id)
  team_id = data.get('team_id')
  if team_id not in {t['id'] for t in teams}:
    team_id = min(teams, key=lambda t: t['players'])['id'] if teams else None
  user_id = str(_uuid.uuid4())
  _run("INSERT INTO User (id, name, role, password) VALUES (%s, %s, 'guest', NULL)", [user_id, name])
  _run("INSERT INTO Participant (userID, eventID, teamID) VALUES (%s, %s, %s)", [user_id, event_id, team_id])
  return jsonify({"status": "success", "received": {"userID": user_id, "name": name, "teamID": team_id}})
