import contextlib
import random
import uuid

from .SQL_manager import get_db

WHEEL_PALETTE = [
  '#fbbf24', '#60a5fa', '#34d399', '#f87171',
  '#c084fc', '#fb923c', '#2dd4bf', '#f472b6',
]

VALID_EFFECT_TYPES = {'add_points', 'deduct_team', 'steal_team', 'none'}
VALID_REWARD_TYPES = {'spin_wheel', 'add_points', 'deduct_team', 'steal_team', 'none'}
VALID_AWARD_TARGETS = {'player', 'team', 'either'}


@contextlib.contextmanager
def db_conn():
  conn = get_db()
  try:
    yield conn
  finally:
    try:
      conn.close()
    except Exception:
      pass


def _select(conn, sql, args=None):
  with conn.cursor() as cur:
    cur.execute(sql, args or [])
    return cur.fetchall()


def _execute(conn, sql, args=None):
  with conn.cursor() as cur:
    cur.execute(sql, args or [])
    rowcount = cur.rowcount
  conn.commit()
  return rowcount


def ensure_mini_events_schema():
  statements = [
    """
    CREATE TABLE IF NOT EXISTS MiniWheel (
      id CHAR(36) PRIMARY KEY,
      event_id CHAR(36) NOT NULL,
      name VARCHAR(255) NOT NULL,
      description TEXT NULL,
      sort_order INT NOT NULL DEFAULT 0,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      INDEX idx_mini_wheel_event (event_id),
      CONSTRAINT fk_mini_wheel_event FOREIGN KEY (event_id) REFERENCES Event(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS MiniWheelItem (
      id CHAR(36) PRIMARY KEY,
      wheel_id CHAR(36) NOT NULL,
      label VARCHAR(255) NOT NULL,
      description TEXT NULL,
      requires_completion TINYINT(1) NOT NULL DEFAULT 1,
      effect_type VARCHAR(32) NOT NULL DEFAULT 'add_points',
      points INT NOT NULL DEFAULT 1,
      colour VARCHAR(32) NOT NULL DEFAULT '#fbbf24',
      sort_order INT NOT NULL DEFAULT 0,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      INDEX idx_wheel_item_wheel (wheel_id),
      CONSTRAINT fk_wheel_item_wheel FOREIGN KEY (wheel_id) REFERENCES MiniWheel(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS PlayerTask (
      id CHAR(36) PRIMARY KEY,
      event_id CHAR(36) NOT NULL,
      user_id CHAR(36) NOT NULL,
      assigned_by CHAR(36) NULL,
      wheel_id CHAR(36) NULL,
      wheel_item_id CHAR(36) NULL,
      title VARCHAR(255) NOT NULL,
      description TEXT NULL,
      status VARCHAR(32) NOT NULL DEFAULT 'pending',
      reward_type VARCHAR(32) NOT NULL DEFAULT 'add_points',
      reward_points INT NOT NULL DEFAULT 0,
      reward_wheel_id CHAR(36) NULL,
      spun_item_id CHAR(36) NULL,
      spun_label VARCHAR(255) NULL,
      spun_effect_type VARCHAR(32) NULL,
      spun_points INT NULL,
      target_team_id CHAR(36) NULL,
      player_claimed_done TINYINT(1) NOT NULL DEFAULT 0,
      result_summary VARCHAR(255) NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      completed_at DATETIME NULL,
      INDEX idx_player_task_event (event_id, status),
      INDEX idx_player_task_user (event_id, user_id, status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS TeamPoint (
      id CHAR(36) PRIMARY KEY,
      event_id CHAR(36) NOT NULL,
      team_id CHAR(36) NOT NULL,
      ref_id CHAR(36) NULL,
      point_number INT NOT NULL,
      reason VARCHAR(255) NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      INDEX idx_team_point_event (event_id, team_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS EventAward (
      id CHAR(36) PRIMARY KEY,
      event_id CHAR(36) NOT NULL,
      name VARCHAR(255) NOT NULL,
      description TEXT NULL,
      target_type VARCHAR(16) NOT NULL DEFAULT 'player',
      sort_order INT NOT NULL DEFAULT 0,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      INDEX idx_event_award_event (event_id),
      CONSTRAINT fk_event_award_event FOREIGN KEY (event_id) REFERENCES Event(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS EventAwardVote (
      id CHAR(36) PRIMARY KEY,
      event_id CHAR(36) NOT NULL,
      award_id CHAR(36) NOT NULL,
      voter_user_id CHAR(36) NOT NULL,
      nominee_id CHAR(36) NOT NULL,
      nominee_type VARCHAR(16) NOT NULL DEFAULT 'player',
      cast_by_user_id CHAR(36) NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      UNIQUE KEY uq_award_voter (award_id, voter_user_id),
      INDEX idx_award_vote_event (event_id, award_id),
      CONSTRAINT fk_award_vote_award FOREIGN KEY (award_id) REFERENCES EventAward(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
    """,
  ]
  try:
    with db_conn() as conn:
      for stmt in statements:
        try:
          _execute(conn, stmt)
        except Exception as exc:
          print(f"Schema statement note: {exc}")

      cols = _select(
        conn,
        """
        SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'Event'
        """,
      )
      existing = {c['COLUMN_NAME'] for c in cols}
      if 'awards_voting_open' not in existing:
        try:
          _execute(conn, "ALTER TABLE Event ADD COLUMN awards_voting_open TINYINT(1) NOT NULL DEFAULT 1")
        except Exception as exc:
          print(f"Column awards_voting_open note: {exc}")
      if 'awards_results_visible' not in existing:
        try:
          _execute(conn, "ALTER TABLE Event ADD COLUMN awards_results_visible TINYINT(1) NOT NULL DEFAULT 0")
        except Exception as exc:
          print(f"Column awards_results_visible note: {exc}")
  except Exception as exc:
    print(f"ensure_mini_events_schema failed: {exc}")


# ---------------- Wheels ----------------

def get_wheels_for_event_sql(event_id):
  try:
    with db_conn() as conn:
      wheels = _select(
        conn,
        "SELECT * FROM MiniWheel WHERE event_id = %s ORDER BY sort_order ASC, created_at ASC",
        [event_id],
      )
      if not wheels:
        return []
      items = _select(
        conn,
        """
        SELECT i.* FROM MiniWheelItem i
        JOIN MiniWheel w ON w.id = i.wheel_id
        WHERE w.event_id = %s
        ORDER BY i.sort_order ASC, i.created_at ASC
        """,
        [event_id],
      )
      by_wheel = {w['id']: [] for w in wheels}
      for item in items:
        item['requires_completion'] = bool(item.get('requires_completion'))
        item['points'] = int(item.get('points') or 0)
        by_wheel.setdefault(item['wheel_id'], []).append(item)
      for w in wheels:
        w['items'] = by_wheel.get(w['id'], [])
      return wheels
  except Exception as exc:
    print(f"get_wheels_for_event_sql failed: {exc}")
    return False


def create_wheel_sql(event_id, name, description=''):
  wheel_id = str(uuid.uuid4())
  try:
    with db_conn() as conn:
      next_row = _select(
        conn,
        "SELECT COALESCE(MAX(sort_order), 0) + 1 AS n FROM MiniWheel WHERE event_id = %s",
        [event_id],
      )
      sort_order = int(next_row[0]['n']) if next_row else 1
      _execute(
        conn,
        "INSERT INTO MiniWheel (id, event_id, name, description, sort_order) VALUES (%s, %s, %s, %s, %s)",
        [wheel_id, event_id, name, description or None, sort_order],
      )
      return {
        "id": wheel_id,
        "event_id": event_id,
        "name": name,
        "description": description or None,
        "sort_order": sort_order,
        "items": [],
      }
  except Exception as exc:
    print(f"create_wheel_sql failed: {exc}")
    return False


def delete_wheel_sql(wheel_id, event_id):
  try:
    with db_conn() as conn:
      _execute(conn, "UPDATE PlayerTask SET wheel_id = NULL WHERE wheel_id = %s AND event_id = %s", [wheel_id, event_id])
      _execute(conn, "UPDATE PlayerTask SET reward_wheel_id = NULL WHERE reward_wheel_id = %s AND event_id = %s", [wheel_id, event_id])
      rows = _execute(conn, "DELETE FROM MiniWheel WHERE id = %s AND event_id = %s", [wheel_id, event_id])
      return rows > 0
  except Exception as exc:
    print(f"delete_wheel_sql failed: {exc}")
    return False


def add_wheel_item_sql(wheel_id, event_id, label, description='', requires_completion=True, effect_type='add_points', points=1, colour=None):
  if effect_type not in VALID_EFFECT_TYPES:
    effect_type = 'add_points'
  try:
    points = int(points or 0)
  except (TypeError, ValueError):
    points = 0
  if effect_type in ('deduct_team', 'steal_team'):
    points = abs(points)
  elif effect_type == 'none':
    points = 0

  item_id = str(uuid.uuid4())
  try:
    with db_conn() as conn:
      owner = _select(conn, "SELECT id FROM MiniWheel WHERE id = %s AND event_id = %s LIMIT 1", [wheel_id, event_id])
      if not owner:
        return False
      count_row = _select(
        conn,
        "SELECT COALESCE(MAX(sort_order), 0) AS m, COUNT(*) AS c FROM MiniWheelItem WHERE wheel_id = %s",
        [wheel_id],
      )
      sort_order = (int(count_row[0]['m']) + 1) if count_row else 1
      item_count = int(count_row[0]['c']) if count_row else 0
      chosen_colour = (colour or '').strip() or WHEEL_PALETTE[item_count % len(WHEEL_PALETTE)]
      _execute(
        conn,
        """
        INSERT INTO MiniWheelItem (id, wheel_id, label, description, requires_completion, effect_type, points, colour, sort_order)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        [item_id, wheel_id, label, description or None, 1 if requires_completion else 0, effect_type, points, chosen_colour, sort_order],
      )
      return {
        "id": item_id,
        "wheel_id": wheel_id,
        "label": label,
        "description": description or None,
        "requires_completion": bool(requires_completion),
        "effect_type": effect_type,
        "points": points,
        "colour": chosen_colour,
        "sort_order": sort_order,
      }
  except Exception as exc:
    print(f"add_wheel_item_sql failed: {exc}")
    return False


def update_wheel_item_sql(item_id, event_id, label, description='', requires_completion=True, effect_type='add_points', points=1, colour='#fbbf24'):
  if effect_type not in VALID_EFFECT_TYPES:
    effect_type = 'add_points'
  try:
    points = int(points or 0)
  except (TypeError, ValueError):
    points = 0
  if effect_type in ('deduct_team', 'steal_team'):
    points = abs(points)
  elif effect_type == 'none':
    points = 0

  try:
    with db_conn() as conn:
      rows = _execute(
        conn,
        """
        UPDATE MiniWheelItem i
        JOIN MiniWheel w ON w.id = i.wheel_id
        SET i.label = %s,
            i.description = %s,
            i.requires_completion = %s,
            i.effect_type = %s,
            i.points = %s,
            i.colour = %s
        WHERE i.id = %s AND w.event_id = %s
        """,
        [label, description or None, 1 if requires_completion else 0, effect_type, points, colour or '#fbbf24', item_id, event_id],
      )
      return rows > 0
  except Exception as exc:
    print(f"update_wheel_item_sql failed: {exc}")
    return False


def delete_wheel_item_sql(item_id, event_id):
  try:
    with db_conn() as conn:
      rows = _execute(
        conn,
        """
        DELETE i FROM MiniWheelItem i
        JOIN MiniWheel w ON w.id = i.wheel_id
        WHERE i.id = %s AND w.event_id = %s
        """,
        [item_id, event_id],
      )
      return rows > 0
  except Exception as exc:
    print(f"delete_wheel_item_sql failed: {exc}")
    return False


def seed_starter_wheel_items_sql(wheel_id, event_id):
  starters = [
    ("Get a stranger's signature", "Write it on a napkin or take a pic", True, "add_points", 3, "#fbbf24"),
    ("Sabotage another team", "Pick another team to lose 2 points", False, "deduct_team", 2, "#f87171"),
    ("Swap an accessory with a stranger", "Show the ref when done", True, "add_points", 3, "#60a5fa"),
    ("Steal 2 points!", "Take 2 points off a rival team for yourself", False, "steal_team", 2, "#34d399"),
    ("Down your current drink", "Bonus points once finished", True, "add_points", 2, "#c084fc"),
    ("Speak in an accent until next pub", "Don't break character!", True, "steal_team", 2, "#fb923c"),
  ]
  created = []
  for label, desc, req, eff, pts, col in starters:
    out = add_wheel_item_sql(wheel_id, event_id, label, desc, req, eff, pts, col)
    if out:
      created.append(out)
  return created if created else False


# ---------------- Team Points ----------------

def get_team_adjustments_sql(event_id):
  try:
    with db_conn() as conn:
      totals = _select(
        conn,
        """
        SELECT t.id AS team_id, COALESCE(SUM(tp.point_number), 0) AS adjustment
        FROM Team t
        LEFT JOIN TeamPoint tp ON tp.team_id = t.id AND tp.event_id = t.eventID
        WHERE t.eventID = %s
        GROUP BY t.id
        """,
        [event_id],
      )
      for row in totals:
        row['adjustment'] = int(row['adjustment'] or 0)
      return totals
  except Exception as exc:
    print(f"get_team_adjustments_sql failed: {exc}")
    return False


# ---------------- Tasks & Wheel Spins ----------------

def _format_effect_summary(effect_type, points, user_name=None, target_team_name=None):
  pts = int(points or 0)
  if effect_type == 'add_points':
    sign = '+' if pts >= 0 else ''
    return f"{sign}{pts} pts" + (f" to {user_name}" if user_name else "")
  if effect_type == 'deduct_team':
    return f"-{abs(pts)} pts" + (f" from {target_team_name}" if target_team_name else " from another team")
  if effect_type == 'steal_team':
    if target_team_name:
      return f"Stole {abs(pts)} pts from {target_team_name}"
    return f"Steal {abs(pts)} pts from another team"
  return "Completed"


def _fetch_task(conn, task_id, event_id):
  rows = _select(
    conn,
    """
    SELECT pt.*,
           u.name AS user_name,
           p.teamID AS user_team_id,
           tm.name AS user_team_name,
           tm.colour AS user_team_colour,
           w.name AS wheel_name,
           rw.name AS reward_wheel_name,
           tt.name AS target_team_name
    FROM PlayerTask pt
    JOIN User u ON u.id = pt.user_id
    LEFT JOIN Participant p ON p.userID = pt.user_id AND p.eventID = pt.event_id
    LEFT JOIN Team tm ON tm.id = p.teamID
    LEFT JOIN MiniWheel w ON w.id = pt.wheel_id
    LEFT JOIN MiniWheel rw ON rw.id = pt.reward_wheel_id
    LEFT JOIN Team tt ON tt.id = pt.target_team_id
    WHERE pt.id = %s AND pt.event_id = %s
    LIMIT 1
    """,
    [task_id, event_id],
  )
  if not rows:
    return None
  row = rows[0]
  row['player_claimed_done'] = bool(row.get('player_claimed_done'))
  row['reward_points'] = int(row.get('reward_points') or 0)
  if row.get('spun_points') is not None:
    row['spun_points'] = int(row['spun_points'])
  return row


def get_event_tasks_sql(event_id, user_id=None):
  try:
    with db_conn() as conn:
      where = "WHERE pt.event_id = %s"
      args = [event_id]
      if user_id:
        where += " AND pt.user_id = %s"
        args.append(user_id)
      rows = _select(
        conn,
        f"""
        SELECT pt.*,
               u.name AS user_name,
               p.teamID AS user_team_id,
               tm.name AS user_team_name,
               tm.colour AS user_team_colour,
               w.name AS wheel_name,
               rw.name AS reward_wheel_name,
               tt.name AS target_team_name
        FROM PlayerTask pt
        JOIN User u ON u.id = pt.user_id
        LEFT JOIN Participant p ON p.userID = pt.user_id AND p.eventID = pt.event_id
        LEFT JOIN Team tm ON tm.id = p.teamID
        LEFT JOIN MiniWheel w ON w.id = pt.wheel_id
        LEFT JOIN MiniWheel rw ON rw.id = pt.reward_wheel_id
        LEFT JOIN Team tt ON tt.id = pt.target_team_id
        {where}
        ORDER BY FIELD(pt.status, 'awaiting_target', 'ready_to_spin', 'pending', 'completed', 'cancelled'),
                 pt.created_at DESC
        LIMIT 80
        """,
        args,
      )
      for row in rows:
        row['player_claimed_done'] = bool(row.get('player_claimed_done'))
        row['reward_points'] = int(row.get('reward_points') or 0)
        if row.get('spun_points') is not None:
          row['spun_points'] = int(row['spun_points'])
      return rows
  except Exception as exc:
    print(f"get_event_tasks_sql failed: {exc}")
    return False


def assign_player_task_sql(
  event_id,
  user_id,
  assigned_by,
  title,
  description='',
  wheel_id=None,
  wheel_item_id=None,
  reward_type='add_points',
  reward_points=1,
  reward_wheel_id=None,
):
  if reward_type not in VALID_REWARD_TYPES:
    reward_type = 'add_points'
  try:
    reward_points = int(reward_points or 0)
  except (TypeError, ValueError):
    reward_points = 0
  if reward_type in ('deduct_team', 'steal_team'):
    reward_points = abs(reward_points)
  elif reward_type in ('none', 'spin_wheel'):
    reward_points = 0

  task_id = str(uuid.uuid4())
  try:
    with db_conn() as conn:
      part = _select(
        conn,
        "SELECT 1 FROM Participant WHERE eventID = %s AND userID = %s LIMIT 1",
        [event_id, user_id],
      )
      if not part:
        return False
      if reward_type == 'spin_wheel':
        rw_id = reward_wheel_id or wheel_id
        if not rw_id:
          return False
        w_check = _select(conn, "SELECT id FROM MiniWheel WHERE id = %s AND event_id = %s LIMIT 1", [rw_id, event_id])
        if not w_check:
          return False
        reward_wheel_id = rw_id
      else:
        reward_wheel_id = None

      _execute(
        conn,
        """
        INSERT INTO PlayerTask (
          id, event_id, user_id, assigned_by, wheel_id, wheel_item_id,
          title, description, status, reward_type, reward_points, reward_wheel_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pending', %s, %s, %s)
        """,
        [
          task_id, event_id, user_id, assigned_by, wheel_id or None, wheel_item_id or None,
          title, description or None, reward_type, reward_points, reward_wheel_id,
        ],
      )
      return _fetch_task(conn, task_id, event_id)
  except Exception as exc:
    print(f"assign_player_task_sql failed: {exc}")
    return False


def assign_random_wheel_task_sql(event_id, user_id, assigned_by, wheel_id=None, override_reward_wheel_id=None):
  try:
    with db_conn() as conn:
      part = _select(
        conn,
        "SELECT 1 FROM Participant WHERE eventID = %s AND userID = %s LIMIT 1",
        [event_id, user_id],
      )
      if not part:
        return False
      if wheel_id:
        items = _select(
          conn,
          """
          SELECT i.* FROM MiniWheelItem i
          JOIN MiniWheel w ON w.id = i.wheel_id
          WHERE w.event_id = %s AND w.id = %s
          """,
          [event_id, wheel_id],
        )
      else:
        items = _select(
          conn,
          """
          SELECT i.* FROM MiniWheelItem i
          JOIN MiniWheel w ON w.id = i.wheel_id
          WHERE w.event_id = %s
          """,
          [event_id],
        )
      if not items:
        return None
      chosen = random.choice(items)
    if override_reward_wheel_id:
      return assign_player_task_sql(
        event_id=event_id,
        user_id=user_id,
        assigned_by=assigned_by,
        title=chosen['label'],
        description=chosen.get('description') or '',
        wheel_id=chosen['wheel_id'],
        wheel_item_id=chosen['id'],
        reward_type='spin_wheel',
        reward_points=0,
        reward_wheel_id=override_reward_wheel_id,
      )
    return assign_player_task_sql(
      event_id=event_id,
      user_id=user_id,
      assigned_by=assigned_by,
      title=chosen['label'],
      description=chosen.get('description') or '',
      wheel_id=chosen['wheel_id'],
      wheel_item_id=chosen['id'],
      reward_type=chosen['effect_type'],
      reward_points=int(chosen.get('points') or 0),
    )
  except Exception as exc:
    print(f"assign_random_wheel_task_sql failed: {exc}")
    return False


def _other_teams_for_user(conn, event_id, user_id):
  part = _select(conn, "SELECT teamID FROM Participant WHERE eventID = %s AND userID = %s LIMIT 1", [event_id, user_id])
  user_team_id = part[0]['teamID'] if part else None
  teams = _select(conn, "SELECT id, name FROM Team WHERE eventID = %s", [event_id])
  return [t for t in teams if t['id'] != user_team_id]


def _apply_direct_effect(conn, event_id, user_id, actor_id, effect_type, points, target_team_id=None, reason=''):
  pts = int(points or 0)
  if effect_type == 'add_points':
    if pts != 0:
      _execute(
        conn,
        "INSERT INTO Point (eventID, refID, userID, point_number) VALUES (%s, %s, %s, %s)",
        [event_id, actor_id, user_id, pts],
      )
    return 'completed', None, _format_effect_summary('add_points', pts)

  if effect_type in ('deduct_team', 'steal_team'):
    abs_pts = abs(pts)
    if abs_pts == 0:
      return 'completed', None, "No points changed"
    other_teams = _other_teams_for_user(conn, event_id, user_id)
    if not other_teams:
      return 'completed', None, "No other teams to target"
    if target_team_id:
      valid_target = next((t for t in _select(conn, "SELECT id, name FROM Team WHERE eventID = %s AND id = %s LIMIT 1", [event_id, target_team_id])), None)
      if not valid_target:
        return None, None, None
      _execute(
        conn,
        "INSERT INTO TeamPoint (id, event_id, team_id, ref_id, point_number, reason) VALUES (%s, %s, %s, %s, %s, %s)",
        [str(uuid.uuid4()), event_id, target_team_id, actor_id, -abs_pts, reason or None],
      )
      if effect_type == 'steal_team':
        _execute(
          conn,
          "INSERT INTO Point (eventID, refID, userID, point_number) VALUES (%s, %s, %s, %s)",
          [event_id, actor_id, user_id, abs_pts],
        )
      return 'completed', target_team_id, _format_effect_summary(effect_type, abs_pts, target_team_name=valid_target['name'])
    return 'awaiting_target', None, _format_effect_summary(effect_type, abs_pts)

  return 'completed', None, "Completed"


def confirm_player_task_sql(task_id, event_id, ref_id, target_team_id=None):
  try:
    with db_conn() as conn:
      task = _fetch_task(conn, task_id, event_id)
      if not task:
        return None
      if task['status'] != 'pending':
        return {"already_processed": True, "task": task}

      reward_type = task['reward_type']
      if reward_type == 'spin_wheel':
        rows = _execute(
          conn,
          "UPDATE PlayerTask SET status = 'ready_to_spin', result_summary = 'Confirmed — ready to spin!' WHERE id = %s AND event_id = %s AND status = 'pending'",
          [task_id, event_id],
        )
        if rows == 0:
          return {"already_processed": True, "task": _fetch_task(conn, task_id, event_id)}
        return {"already_processed": False, "task": _fetch_task(conn, task_id, event_id)}

      if reward_type in ('deduct_team', 'steal_team') and target_team_id is None:
        other_teams = _other_teams_for_user(conn, event_id, task['user_id'])
        if other_teams and abs(int(task['reward_points'] or 0)) > 0:
          rows = _execute(
            conn,
            "UPDATE PlayerTask SET status = 'awaiting_target', result_summary = %s WHERE id = %s AND event_id = %s AND status = 'pending'",
            [_format_effect_summary(reward_type, task['reward_points']), task_id, event_id],
          )
          if rows == 0:
            return {"already_processed": True, "task": _fetch_task(conn, task_id, event_id)}
          return {"already_processed": False, "task": _fetch_task(conn, task_id, event_id)}

      rows = _execute(
        conn,
        "UPDATE PlayerTask SET status = 'processing' WHERE id = %s AND event_id = %s AND status = 'pending'",
        [task_id, event_id],
      )
      if rows == 0:
        return {"already_processed": True, "task": _fetch_task(conn, task_id, event_id)}

      new_status, used_team_id, summary = _apply_direct_effect(
        conn,
        event_id,
        task['user_id'],
        ref_id,
        reward_type,
        task['reward_points'],
        target_team_id=target_team_id,
        reason=task['title'],
      )
      if new_status is None:
        _execute(conn, "UPDATE PlayerTask SET status = 'pending' WHERE id = %s", [task_id])
        return False

      _execute(
        conn,
        """
        UPDATE PlayerTask
        SET status = %s,
            target_team_id = %s,
            result_summary = %s,
            completed_at = IF(%s = 'completed', NOW(), NULL)
        WHERE id = %s
        """,
        [new_status, used_team_id, summary, new_status, task_id],
      )
      return {"already_processed": False, "task": _fetch_task(conn, task_id, event_id)}
  except Exception as exc:
    print(f"confirm_player_task_sql failed: {exc}")
    return False


def spin_task_wheel_sql(task_id, event_id, actor_user_id, actor_is_admin):
  try:
    with db_conn() as conn:
      task = _fetch_task(conn, task_id, event_id)
      if not task:
        return None
      if not actor_is_admin and task['user_id'] != actor_user_id:
        return 'forbidden'
      if task['status'] != 'ready_to_spin':
        return {"already_spun": True, "task": task}

      wheel_id = task.get('reward_wheel_id') or task.get('wheel_id')
      items = _select(
        conn,
        "SELECT * FROM MiniWheelItem WHERE wheel_id = %s ORDER BY sort_order ASC, created_at ASC",
        [wheel_id],
      )
      if not items:
        return 'empty_wheel'

      chosen_index = random.randrange(len(items))
      chosen = items[chosen_index]

      rows = _execute(
        conn,
        "UPDATE PlayerTask SET status = 'spinning' WHERE id = %s AND event_id = %s AND status = 'ready_to_spin'",
        [task_id, event_id],
      )
      if rows == 0:
        return {"already_spun": True, "task": _fetch_task(conn, task_id, event_id)}

      new_status, used_team_id, summary = _apply_direct_effect(
        conn,
        event_id,
        task['user_id'],
        actor_user_id,
        chosen['effect_type'],
        int(chosen.get('points') or 0),
        reason=f"Wheel: {chosen['label']}",
      )
      _execute(
        conn,
        """
        UPDATE PlayerTask
        SET status = %s,
            spun_item_id = %s,
            spun_label = %s,
            spun_effect_type = %s,
            spun_points = %s,
            target_team_id = %s,
            result_summary = %s,
            completed_at = IF(%s = 'completed', NOW(), NULL)
        WHERE id = %s
        """,
        [
          new_status,
          chosen['id'],
          chosen['label'],
          chosen['effect_type'],
          int(chosen.get('points') or 0),
          used_team_id,
          summary,
          new_status,
          task_id,
        ],
      )
      return {
        "already_spun": False,
        "chosen_index": chosen_index,
        "chosen_item": chosen,
        "task": _fetch_task(conn, task_id, event_id),
      }
  except Exception as exc:
    print(f"spin_task_wheel_sql failed: {exc}")
    return False


def spin_direct_wheel_for_player_sql(event_id, user_id, ref_id, wheel_id):
  try:
    with db_conn() as conn:
      part = _select(
        conn,
        "SELECT 1 FROM Participant WHERE eventID = %s AND userID = %s LIMIT 1",
        [event_id, user_id],
      )
      if not part:
        return None
      wheel = _select(conn, "SELECT * FROM MiniWheel WHERE id = %s AND event_id = %s LIMIT 1", [wheel_id, event_id])
      if not wheel:
        return None
      items = _select(
        conn,
        "SELECT * FROM MiniWheelItem WHERE wheel_id = %s ORDER BY sort_order ASC, created_at ASC",
        [wheel_id],
      )
      if not items:
        return 'empty_wheel'

      chosen_index = random.randrange(len(items))
      chosen = items[chosen_index]
      task_id = str(uuid.uuid4())
      req = bool(chosen.get('requires_completion'))
      pts = int(chosen.get('points') or 0)
      eff = chosen['effect_type']

      if req:
        _execute(
          conn,
          """
          INSERT INTO PlayerTask (
            id, event_id, user_id, assigned_by, wheel_id, wheel_item_id,
            title, description, status, reward_type, reward_points,
            spun_item_id, spun_label, spun_effect_type, spun_points, result_summary
          ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pending', %s, %s, %s, %s, %s, %s, %s)
          """,
          [
            task_id, event_id, user_id, ref_id, wheel_id, chosen['id'],
            chosen['label'], chosen.get('description') or None, eff, pts,
            chosen['id'], chosen['label'], eff, pts,
            f"Task spun: {_format_effect_summary(eff, pts)}",
          ],
        )
      else:
        new_status, used_team_id, summary = _apply_direct_effect(
          conn, event_id, user_id, ref_id, eff, pts, reason=f"Wheel: {chosen['label']}"
        )
        _execute(
          conn,
          """
          INSERT INTO PlayerTask (
            id, event_id, user_id, assigned_by, wheel_id, wheel_item_id,
            title, description, status, reward_type, reward_points,
            spun_item_id, spun_label, spun_effect_type, spun_points,
            target_team_id, result_summary, completed_at
          ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, IF(%s = 'completed', NOW(), NULL))
          """,
          [
            task_id, event_id, user_id, ref_id, wheel_id, chosen['id'],
            chosen['label'], chosen.get('description') or None, new_status, eff, pts,
            chosen['id'], chosen['label'], eff, pts,
            used_team_id, summary, new_status,
          ],
        )

      return {
        "chosen_index": chosen_index,
        "chosen_item": chosen,
        "task": _fetch_task(conn, task_id, event_id),
      }
  except Exception as exc:
    print(f"spin_direct_wheel_for_player_sql failed: {exc}")
    return False


def apply_task_target_sql(task_id, event_id, target_team_id, actor_user_id, actor_is_admin):
  try:
    with db_conn() as conn:
      task = _fetch_task(conn, task_id, event_id)
      if not task:
        return None
      if not actor_is_admin and task['user_id'] != actor_user_id:
        return 'forbidden'
      if task['status'] != 'awaiting_target':
        return {"already_applied": True, "task": task}

      team_row = _select(conn, "SELECT id, name FROM Team WHERE id = %s AND eventID = %s LIMIT 1", [target_team_id, event_id])
      if not team_row:
        return 'invalid_team'

      effect_type = task.get('spun_effect_type') or task['reward_type']
      points = task.get('spun_points') if task.get('spun_points') is not None else task['reward_points']
      abs_pts = abs(int(points or 0))
      summary = _format_effect_summary(effect_type, abs_pts, target_team_name=team_row[0]['name'])

      rows = _execute(
        conn,
        """
        UPDATE PlayerTask
        SET status = 'completed',
            target_team_id = %s,
            result_summary = %s,
            completed_at = NOW()
        WHERE id = %s AND event_id = %s AND status = 'awaiting_target'
        """,
        [target_team_id, summary, task_id, event_id],
      )
      if rows == 0:
        return {"already_applied": True, "task": _fetch_task(conn, task_id, event_id)}

      if abs_pts > 0:
        _execute(
          conn,
          "INSERT INTO TeamPoint (id, event_id, team_id, ref_id, point_number, reason) VALUES (%s, %s, %s, %s, %s, %s)",
          [str(uuid.uuid4()), event_id, target_team_id, actor_user_id, -abs_pts, task.get('spun_label') or task['title']],
        )
        if effect_type == 'steal_team':
          _execute(
            conn,
            "INSERT INTO Point (eventID, refID, userID, point_number) VALUES (%s, %s, %s, %s)",
            [event_id, actor_user_id, task['user_id'], abs_pts],
          )

      return {"already_applied": False, "task": _fetch_task(conn, task_id, event_id)}
  except Exception as exc:
    print(f"apply_task_target_sql failed: {exc}")
    return False


def claim_task_done_sql(task_id, event_id, user_id):
  try:
    with db_conn() as conn:
      rows = _execute(
        conn,
        """
        UPDATE PlayerTask SET player_claimed_done = 1
        WHERE id = %s AND event_id = %s AND user_id = %s AND status = 'pending'
        """,
        [task_id, event_id, user_id],
      )
      return _fetch_task(conn, task_id, event_id) if rows >= 0 else False
  except Exception as exc:
    print(f"claim_task_done_sql failed: {exc}")
    return False


def cancel_player_task_sql(task_id, event_id):
  try:
    with db_conn() as conn:
      rows = _execute(
        conn,
        """
        UPDATE PlayerTask SET status = 'cancelled'
        WHERE id = %s AND event_id = %s AND status IN ('pending', 'ready_to_spin', 'awaiting_target')
        """,
        [task_id, event_id],
      )
      return rows > 0
  except Exception as exc:
    print(f"cancel_player_task_sql failed: {exc}")
    return False


# ---------------- Awards ----------------

def get_awards_for_event_sql(event_id):
  try:
    with db_conn() as conn:
      return _select(
        conn,
        "SELECT * FROM EventAward WHERE event_id = %s ORDER BY sort_order ASC, created_at ASC",
        [event_id],
      )
  except Exception as exc:
    print(f"get_awards_for_event_sql failed: {exc}")
    return False


def create_award_sql(event_id, name, description='', target_type='player'):
  if target_type not in VALID_AWARD_TARGETS:
    target_type = 'player'
  award_id = str(uuid.uuid4())
  try:
    with db_conn() as conn:
      next_row = _select(
        conn,
        "SELECT COALESCE(MAX(sort_order), 0) + 1 AS n FROM EventAward WHERE event_id = %s",
        [event_id],
      )
      sort_order = int(next_row[0]['n']) if next_row else 1
      _execute(
        conn,
        "INSERT INTO EventAward (id, event_id, name, description, target_type, sort_order) VALUES (%s, %s, %s, %s, %s, %s)",
        [award_id, event_id, name, description or None, target_type, sort_order],
      )
      return {
        "id": award_id,
        "event_id": event_id,
        "name": name,
        "description": description or None,
        "target_type": target_type,
        "sort_order": sort_order,
      }
  except Exception as exc:
    print(f"create_award_sql failed: {exc}")
    return False


def delete_award_sql(award_id, event_id):
  try:
    with db_conn() as conn:
      rows = _execute(conn, "DELETE FROM EventAward WHERE id = %s AND event_id = %s", [award_id, event_id])
      return rows > 0
  except Exception as exc:
    print(f"delete_award_sql failed: {exc}")
    return False


def seed_default_awards_sql(event_id):
  defaults = [
    ("Best Dressed", "Best outfit of the crawl", "player"),
    ("Best Group Chemistry", "Best team energy & vibes all night", "team"),
    ("Best Handshake", "Best handshake / greeting", "player"),
    ("Life of the Party", "Brought the best energy all crawl", "player"),
  ]
  try:
    with db_conn() as conn:
      existing = _select(conn, "SELECT LOWER(name) AS lname FROM EventAward WHERE event_id = %s", [event_id])
      existing_names = {r['lname'] for r in existing}
    created = []
    for name, desc, target in defaults:
      if name.lower() not in existing_names:
        row = create_award_sql(event_id, name, desc, target)
        if row:
          created.append(row)
    return created
  except Exception as exc:
    print(f"seed_default_awards_sql failed: {exc}")
    return False


def get_awards_settings_sql(event_id):
  try:
    with db_conn() as conn:
      rows = _select(
        conn,
        "SELECT awards_voting_open, awards_results_visible FROM Event WHERE id = %s LIMIT 1",
        [event_id],
      )
      if not rows:
        return {"voting_open": True, "results_visible": False}
      return {
        "voting_open": bool(rows[0].get('awards_voting_open', 1)),
        "results_visible": bool(rows[0].get('awards_results_visible', 0)),
      }
  except Exception as exc:
    print(f"get_awards_settings_sql failed: {exc}")
    return {"voting_open": True, "results_visible": False}


def set_awards_settings_sql(event_id, voting_open=None, results_visible=None):
  try:
    with db_conn() as conn:
      if voting_open is not None:
        _execute(conn, "UPDATE Event SET awards_voting_open = %s WHERE id = %s", [1 if voting_open else 0, event_id])
      if results_visible is not None:
        _execute(conn, "UPDATE Event SET awards_results_visible = %s WHERE id = %s", [1 if results_visible else 0, event_id])
      rows = _select(
        conn,
        "SELECT awards_voting_open, awards_results_visible FROM Event WHERE id = %s LIMIT 1",
        [event_id],
      )
      if not rows:
        return False
      return {
        "voting_open": bool(rows[0].get('awards_voting_open', 1)),
        "results_visible": bool(rows[0].get('awards_results_visible', 0)),
      }
  except Exception as exc:
    print(f"set_awards_settings_sql failed: {exc}")
    return False


def cast_award_vote_sql(event_id, award_id, voter_user_id, nominee_id, nominee_type, cast_by_user_id, actor_is_admin):
  if nominee_type not in ('player', 'team'):
    return 'bad_request'
  try:
    with db_conn() as conn:
      event_row = _select(conn, "SELECT awards_voting_open FROM Event WHERE id = %s LIMIT 1", [event_id])
      if not event_row:
        return 'not_found'
      if not actor_is_admin and not bool(event_row[0].get('awards_voting_open', 1)):
        return 'voting_closed'

      award_rows = _select(conn, "SELECT id, target_type FROM EventAward WHERE id = %s AND event_id = %s LIMIT 1", [award_id, event_id])
      if not award_rows:
        return 'not_found'
      target_type = award_rows[0]['target_type']
      if target_type != 'either' and target_type != nominee_type:
        return 'invalid_nominee'

      # Voter must exist in User (usually Participant, or admin voting for themselves)
      voter_exists = _select(conn, "SELECT id FROM User WHERE id = %s LIMIT 1", [voter_user_id])
      if not voter_exists:
        return 'invalid_voter'

      if nominee_type == 'player':
        nom_ok = _select(conn, "SELECT 1 FROM Participant WHERE eventID = %s AND userID = %s LIMIT 1", [event_id, nominee_id])
      else:
        nom_ok = _select(conn, "SELECT 1 FROM Team WHERE eventID = %s AND id = %s LIMIT 1", [event_id, nominee_id])
      if not nom_ok:
        return 'invalid_nominee'

      _execute(
        conn,
        """
        INSERT INTO EventAwardVote (id, event_id, award_id, voter_user_id, nominee_id, nominee_type, cast_by_user_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          nominee_id = VALUES(nominee_id),
          nominee_type = VALUES(nominee_type),
          cast_by_user_id = VALUES(cast_by_user_id)
        """,
        [str(uuid.uuid4()), event_id, award_id, voter_user_id, nominee_id, nominee_type, cast_by_user_id],
      )
      return True
  except Exception as exc:
    print(f"cast_award_vote_sql failed: {exc}")
    return False


def get_award_votes_summary_sql(event_id, viewer_user_id, include_tally=False, include_all_voters=False):
  try:
    with db_conn() as conn:
      my_rows = _select(
        conn,
        "SELECT award_id, nominee_id, nominee_type FROM EventAwardVote WHERE event_id = %s AND voter_user_id = %s",
        [event_id, viewer_user_id],
      )
      my_votes = {
        r['award_id']: {"nominee_id": r['nominee_id'], "nominee_type": r['nominee_type']}
        for r in my_rows
      }
      result = {"my_votes": my_votes}

      if include_tally or include_all_voters:
        all_votes = _select(
          conn,
          """
          SELECT v.award_id, v.voter_user_id, v.nominee_id, v.nominee_type,
                 u.name AS player_nominee_name,
                 pt.colour AS player_team_colour,
                 t.name AS team_nominee_name,
                 t.colour AS team_colour
          FROM EventAwardVote v
          LEFT JOIN User u ON v.nominee_type = 'player' AND u.id = v.nominee_id
          LEFT JOIN Participant p ON v.nominee_type = 'player' AND p.userID = v.nominee_id AND p.eventID = v.event_id
          LEFT JOIN Team pt ON pt.id = p.teamID
          LEFT JOIN Team t ON v.nominee_type = 'team' AND t.id = v.nominee_id
          WHERE v.event_id = %s
          """,
          [event_id],
        )

        if include_tally:
          tally_map = {}
          for v in all_votes:
            aid = v['award_id']
            key = f"{v['nominee_type']}:{v['nominee_id']}"
            bucket = tally_map.setdefault(aid, {})
            if key not in bucket:
              name = v['team_nominee_name'] if v['nominee_type'] == 'team' else v['player_nominee_name']
              colour = v['team_colour'] if v['nominee_type'] == 'team' else v['player_team_colour']
              bucket[key] = {
                "nominee_id": v['nominee_id'],
                "nominee_type": v['nominee_type'],
                "nominee_name": name or "Unknown",
                "colour": colour or "#fbbf24",
                "votes": 0,
              }
            bucket[key]['votes'] += 1
          tally = {}
          for aid, entries in tally_map.items():
            tally[aid] = sorted(entries.values(), key=lambda x: (-x['votes'], str(x['nominee_name']).lower()))
          result["tally"] = tally

        if include_all_voters:
          by_voter = {}
          for v in all_votes:
            by_voter.setdefault(v['voter_user_id'], {})[v['award_id']] = {
              "nominee_id": v['nominee_id'],
              "nominee_type": v['nominee_type'],
            }
          result["votes_by_voter"] = by_voter

      return result
  except Exception as exc:
    print(f"get_award_votes_summary_sql failed: {exc}")
    return False
