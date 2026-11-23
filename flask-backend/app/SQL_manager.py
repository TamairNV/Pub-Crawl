import os

import dotenv
import pymysql
import pymysql.cursors
from flask import g

dotenv.load_dotenv()

host = os.getenv("DB_HOST")
user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
database = os.getenv("DB_NAME")
port = int(os.getenv("DB_PORT"))


def get_db():
  return pymysql.connect(
    host=host,
    user=user,
    password=password,
    database=database,
    port=port,
    cursorclass=pymysql.cursors.DictCursor)
  #if current request doesn't have a DB connection yet make one
  if 'db' not in g:
    g.db = pymysql.connect(
      host=host,
      user=user,
      password=password,
      database=database,
      port=port,
      cursorclass=pymysql.cursors.DictCursor
    )
  return g.db

def run_query(connection, sql, args=None):

  with connection.cursor() as cursor:
    cursor.execute(sql, args)
    if sql.strip().upper().startswith("SELECT"):
      return cursor.fetchall()

    connection.commit()
    return cursor.rowcount


def _close_conn(connection):
  """Close a pymysql connection cleanly without raising on cleanup."""
  if connection:
    try:
      connection.close()
    except Exception:
      pass


def _run(sql, args=None):
  """Execute a single SQL query and always close its connection."""
  connection = None
  try:
    connection = get_db()
    return run_query(connection, sql, args)
  finally:
    _close_conn(connection)

import uuid

import uuid
import json
from datetime import datetime


def get_all_users_sql():
  query = "SELECT id, name, role, teamID, created_at, updated_at FROM User"
  try:
    return _run(query, [])
  except Exception as e:
    print(f"Query Failed: {e}")
    return False

def select_users_sql(user_ids):
  format_strings = ','.join(['%s'] * len(user_ids))
  query = f"SELECT * FROM users WHERE id IN ({format_strings})"
  try:
    return _run(query, [id])
  except Exception as e:
    print(f"Query Failed: {e}")
    return False

def is_name_taken(name):
  query = "SELECT * FROM User WHERE name = %s LIMIT 1"
  try:
    results = _run(query, [name])
    return bool(results)
  except Exception as e:
    print(f"Query Failed: {e}")
    return False

def create_user_sql(name,passkey,role = "player"):
  query = "INSERT INTO User (name,password,role) VALUES (%s,%s,%s)"
  try:
    _run(query, [name,passkey,role])
    return True
  except Exception as e:
    print(f"Query Failed: {e}")
    return False


def get_user_data_from_name_sql(name):
  query = "SELECT * FROM User WHERE name = %s LIMIT 1"
  try:
    return _run(query, [name])
  except Exception as e:
    print(f"Query Failed: {e}")
    return False


def create_event_sql(id,name):
  query = "INSERT INTO Event (id,name) VALUES (%s,%s)"
  try:
    out = _run(query, [id,name])
    return {
      "id": str(id),
      "out": out
    }
  except Exception as e:
    print(f"Query Failed: {e}")
    return False

_HAS_DELETED_AT_COLUMN = False


def has_deleted_at_column(connection=None):
  global _HAS_DELETED_AT_COLUMN
  if _HAS_DELETED_AT_COLUMN:
    return True
  owns_conn = False
  try:
    if connection is None:
      connection = get_db()
      owns_conn = True
    with connection.cursor() as cursor:
      cursor.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'Event'
          AND COLUMN_NAME = 'deleted_at'
        """
      )
      row = cursor.fetchone()
      cnt = row['cnt'] if isinstance(row, dict) else (row[0] if row else 0)
      if cnt and int(cnt) > 0:
        _HAS_DELETED_AT_COLUMN = True
        return True
      return False
  except Exception as e:
    print(f"has_deleted_at_column failed: {e}")
    return False
  finally:
    if owns_conn and connection:
      try:
        connection.close()
      except Exception:
        pass


def get_all_events_sql():
  connection = None
  try:
    connection = get_db()
    if has_deleted_at_column(connection):
      query = "SELECT * FROM Event WHERE deleted_at IS NULL ORDER BY created_at DESC"
    else:
      query = "SELECT * FROM Event ORDER BY created_at DESC"
    return run_query(connection, query, [])

  except Exception as e:
    print(f"Query Failed: {e}")
    return False
  finally:
    if connection:
      try:
        connection.close()
      except Exception:
        pass


def soft_delete_event_sql(event_id):
  connection = None
  try:
    connection = get_db()
    if not has_deleted_at_column(connection):
      return 'schema_missing'
    with connection.cursor() as cursor:
      cursor.execute(
        "UPDATE Event SET deleted_at = NOW() WHERE id = %s AND deleted_at IS NULL",
        [event_id],
      )
      updated = cursor.rowcount
    connection.commit()
    return True if updated > 0 else None
  except Exception as e:
    if connection:
      try:
        connection.rollback()
      except Exception:
        pass
    print(f"soft_delete_event_sql failed: {e}")
    return False
  finally:
    if connection:
      try:
        connection.close()
      except Exception:
        pass


def get_deleted_events_sql():
  connection = None
  try:
    connection = get_db()
    if not has_deleted_at_column(connection):
      return 'schema_missing'
    query = "SELECT * FROM Event WHERE deleted_at IS NOT NULL ORDER BY deleted_at DESC, created_at DESC"
    return run_query(connection, query, [])
  except Exception as e:
    print(f"get_deleted_events_sql failed: {e}")
    return False
  finally:
    if connection:
      try:
        connection.close()
      except Exception:
        pass


def restore_event_sql(event_id):
  connection = None
  try:
    connection = get_db()
    if not has_deleted_at_column(connection):
      return 'schema_missing'
    with connection.cursor() as cursor:
      cursor.execute(
        "UPDATE Event SET deleted_at = NULL WHERE id = %s AND deleted_at IS NOT NULL",
        [event_id],
      )
      updated = cursor.rowcount
    connection.commit()
    return True if updated > 0 else None
  except Exception as e:
    if connection:
      try:
        connection.rollback()
      except Exception:
        pass
    print(f"restore_event_sql failed: {e}")
    return False
  finally:
    if connection:
      try:
        connection.close()
      except Exception:
        pass


def delete_event_sql(event_id, only_deleted=False):
  connection = None
  try:
    connection = get_db()
    has_del = has_deleted_at_column(connection)
    if only_deleted and not has_del:
      return 'schema_missing'
    with connection.cursor() as cursor:
      if only_deleted and has_del:
        cursor.execute("SELECT id FROM Event WHERE id = %s AND deleted_at IS NOT NULL LIMIT 1", [event_id])
      else:
        cursor.execute("SELECT id FROM Event WHERE id = %s LIMIT 1", [event_id])
      if not cursor.fetchone():
        return None

      cursor.execute("SELECT id FROM Photo WHERE event_id = %s", [event_id])
      photos = [r['id'] for r in cursor.fetchall()]

      cursor.execute("DELETE FROM TeamPoint WHERE event_id = %s", [event_id])
      cursor.execute("DELETE FROM PlayerTask WHERE event_id = %s", [event_id])
      cursor.execute("DELETE FROM EventAwardVote WHERE event_id = %s", [event_id])
      cursor.execute("DELETE FROM EventAward WHERE event_id = %s", [event_id])
      cursor.execute("DELETE FROM MiniWheelItem WHERE wheel_id IN (SELECT id FROM MiniWheel WHERE event_id = %s)", [event_id])
      cursor.execute("DELETE FROM MiniWheel WHERE event_id = %s", [event_id])
      cursor.execute("DELETE FROM Point WHERE eventID = %s", [event_id])
      cursor.execute("DELETE FROM Participant WHERE eventID = %s", [event_id])
      cursor.execute("DELETE FROM Rule WHERE event_id = %s", [event_id])
      cursor.execute("DELETE FROM Pub WHERE eventID = %s", [event_id])
      cursor.execute("DELETE FROM Photo WHERE event_id = %s", [event_id])
      cursor.execute("DELETE FROM Team WHERE eventID = %s", [event_id])
      cursor.execute("DELETE FROM Event WHERE id = %s", [event_id])
      deleted = cursor.rowcount
    connection.commit()
    if deleted <= 0:
      return None
    return photos
  except Exception as e:
    if connection:
      try:
        connection.rollback()
      except Exception:
        pass
    print(f"delete_event_sql failed: {e}")
    return False
  finally:
    if connection:
      try:
        connection.close()
      except Exception:
        pass


def reset_event_data_sql(event_id, clear_media=True):
  connection = None
  try:
    connection = get_db()
    with connection.cursor() as cursor:
      if has_deleted_at_column(connection):
        cursor.execute("SELECT id FROM Event WHERE id = %s AND deleted_at IS NULL LIMIT 1", [event_id])
      else:
        cursor.execute("SELECT id FROM Event WHERE id = %s LIMIT 1", [event_id])
      if not cursor.fetchone():
        return None

      cursor.execute("DELETE FROM Point WHERE eventID = %s", [event_id])
      points_cleared = cursor.rowcount

      cursor.execute("DELETE FROM TeamPoint WHERE event_id = %s", [event_id])
      team_points_cleared = cursor.rowcount

      cursor.execute("DELETE FROM PlayerTask WHERE event_id = %s", [event_id])
      tasks_cleared = cursor.rowcount

      cursor.execute("DELETE FROM EventAwardVote WHERE event_id = %s", [event_id])
      votes_cleared = cursor.rowcount

      photos = []
      photos_cleared = 0
      if clear_media:
        cursor.execute("SELECT id FROM Photo WHERE event_id = %s", [event_id])
        photos = [r['id'] for r in cursor.fetchall()]
        cursor.execute("DELETE FROM Photo WHERE event_id = %s", [event_id])
        photos_cleared = cursor.rowcount

      cursor.execute(
        """
        UPDATE Event
        SET current_pub_id = NULL,
            awards_voting_open = 1,
            awards_results_visible = 0
        WHERE id = %s
        """,
        [event_id],
      )
    connection.commit()
    return {
      "photos": photos,
      "cleared": {
        "points": int(points_cleared or 0),
        "team_points": int(team_points_cleared or 0),
        "tasks": int(tasks_cleared or 0),
        "votes": int(votes_cleared or 0),
        "photos": int(photos_cleared or 0),
      },
    }
  except Exception as e:
    if connection:
      try:
        connection.rollback()
      except Exception:
        pass
    print(f"reset_event_data_sql failed: {e}")
    return False
  finally:
    if connection:
      try:
        connection.close()
      except Exception:
        pass

def get_all_teams_sql(eventID):
  query = "SELECT * FROM Team WHERE eventID = %s;"
  try:
    return _run(query, [eventID])
  except Exception as e:
    print(f"Query Failed: {e}")
    return False

def create_new_team_sql(team_name,team_colour,event_id):
  query = "INSERT INTO Team (id,name,colour,eventID) VALUES (%s,%s,%s,%s)"
  id = uuid.uuid1()
  try:
    out = _run(query, [id,team_name,team_colour,event_id])
    return {
      "id": str(id),
      "out": out
    }
  except Exception as e:
    print(f"Query Failed: {e}")
    return False


def create_participants(people):
  query = "INSERT INTO Participant (userID, eventID, teamID) VALUES (%s, %s, %s);"
  params = [(p['userId'], p['eventId'], p['teamId']) for p in people]
  connection = None
  try:
    connection = get_db()
    cursor = connection.cursor()
    cursor.executemany(query, params)
    connection.commit()
    return True
  except Exception as e:
    print(f"Query Failed: {e}")
    return False
  finally:
    _close_conn(connection)


def get_users_in_event_sql(event_id):
    query = """
            SELECT
              p.eventID,
              p.teamID,
              p.userID,
              u.name,
              t.name AS teamName
            FROM Participant as p
                   JOIN User as u ON p.userID = u.id
                   JOIN Team as t ON p.teamID = t.id
            WHERE p.eventID = %s;
    """
    try:
      return _run(query, [event_id])
    except Exception as e:
      print(f"Query Failed: {e}")
      return False

def get_teams_in_event_sql(event_id):
  query = "SELECT * FROM Team WHERE eventID = %s;"
  try:
    return _run(query, [event_id])
  except Exception as e:
    print(f"Query Failed: {e}")
    return False

def update_user_team_sql(event_id,user_id,new_team_id):
  query = "UPDATE Participant SET teamID = %s WHERE userID = %s and eventID = %s"
  try:
    return _run(query, [new_team_id,user_id,event_id])
  except Exception as e:
    print(f"Query Failed: {e}")
    return False

def add_new_location_sql(name,event_id,index):
  id = str(uuid.uuid1())
  query = "INSERT INTO Pub (id,eventID,name,order_index) VALUES (%s,%s,%s,%s)"
  try:
    out = _run(query, [id,event_id,name,index])
    return {
      "id": id,
      "out": out
    }
  except Exception as e:
    print(f"Query Failed: {e}")
    return False


def add_new_rule_sql(pub_id,name,description,event_id):
  query = "INSERT INTO Rule (pubID,name,description,event_id) VALUES (%s,%s,%s,%s)"
  connection = None
  try:
    connection = get_db()
    if pub_id:
      run_query(connection, "DELETE FROM Rule WHERE pubID = %s", [pub_id])
    params = [pub_id,name,description,event_id]
    return run_query(connection, query, params)
  except Exception as e:
    print(f"Query Failed: {e}")
    return False
  finally:
    _close_conn(connection)

def set_pub_rule_sql(pub_id, name, description, event_id):
  connection = None
  try:
    connection = get_db()
    run_query(connection, "DELETE FROM Rule WHERE pubID = %s", [pub_id])
    if name:
      query = "INSERT INTO Rule (pubID,name,description,event_id) VALUES (%s,%s,%s,%s)"
      run_query(connection, query, [pub_id, name, description, event_id])
    return True
  except Exception as e:
    print(f"Query Failed: {e}")
    return False
  finally:
    _close_conn(connection)

def get_all_base_rules_sql(event_id):
  query = "SELECT * FROM Rule WHERE event_id = %s and pubID IS NULL"
  try:
    return _run(query, [event_id])
  except Exception as e:
    print(f"Query Failed: {e}")
    return False

def get_location_rules_sql(event_id):
  query = """
          SELECT
            r.id as ruleId,
            r.name as ruleName,
            r.description as ruleDescription,
            p.name as pubName,
            p.order_index,
            p.id
          FROM Pub as p
                 LEFT JOIN Rule as r on r.pubID = p.id
          WHERE p.eventID = %s
          ORDER BY p.order_index ASC;
          """
  try:
    return _run(query, [event_id])
  except Exception as e:
    print(f"Query Failed: {e}")
    return False

def remove_user_sql(event_id,user_id):
  query = "DELETE FROM Participant WHERE eventID = %s and userID = %s"
  try:
    return _run(query, [event_id,user_id])
  except Exception as e:
    print(f"Query Failed: {e}")
    return False


def remove_base_rule_sql(rule_id):
  query = "DELETE FROM Rule WHERE id = %s"
  try:
    return _run(query, [rule_id])
  except Exception as e:
    print(f"Query Failed: {e}")
    return False

def remove_location_sql(pub_id):
  query = "DELETE FROM Rule WHERE pubID = %s"
  query2 = "DELETE FROM Pub WHERE id = %s;"
  connection = None
  params = [pub_id]
  try:
    connection = get_db()
    out = run_query(connection, query, params)
    out2 = run_query(connection, query2, params)
    return [out, out2]
  except Exception as e:
    print(f"Query Failed: {e}")
    return False
  finally:
    _close_conn(connection)

def get_user_points_sql(event_id):
  query = """
          SELECT
            p.userID,
            COALESCE(SUM(pt.point_number), 0) AS total_points
          FROM Participant p
                 LEFT JOIN Point pt ON p.userID = pt.userID AND p.eventID = pt.eventID
          WHERE p.eventID = %s
          GROUP BY p.userID
          ORDER BY total_points ASC;
  """
  try:
    return _run(query, [event_id])
  except Exception as e:
    print(f"Query Failed: {e}")
    return False


def give_user_points_sql(event_id,user_id,points,admin_id):
  query = "INSERT INTO Point (eventID,refID,userID,point_number) VALUES (%s,%s,%s,%s)"
  try:
    return _run(query, [event_id,admin_id,user_id,points])
  except Exception as e:
    print(f"Query Failed: {e}")
    return False


def events_user_is_in_sql(user_id):
  connection = None
  try:
    connection = get_db()
    if has_deleted_at_column(connection):
      query = """
            SELECT *
            FROM Participant p
                   JOIN Event e ON e.id = p.eventID
            WHERE p.userID = %s
              AND e.deleted_at IS NULL
            ORDER BY e.created_at DESC;
      """
    else:
      query = """
            SELECT *
            FROM Participant p
                   JOIN Event e ON e.id = p.eventID
            WHERE p.userID = %s
            ORDER BY e.created_at DESC;
      """
    return run_query(connection, query, [user_id])

  except Exception as e:
    print(f"Query Failed: {e}")
    return False
  finally:
    if connection:
      try:
        connection.close()
      except Exception:
        pass


def save_photo_ids_sql(user_id,event_id,photos):
  query = """
  INSERT INTO Photo (id, user_id,event_id,time_taken,latitude,longitude) VALUES(%s,%s,%s,%s,%s,%s)
  """
  print(photos)
  connection = None
  out = None
  try:
    connection = get_db()
    for photo in photos:
      print("saved ")
      params = [photo['id'],user_id,event_id,photo['time_taken'],photo['latitude'],photo['longitude']]

      out = run_query(connection, query, params)
    return out
  except Exception as e:
    print(f"Query Failed: {e}")
    return False
  finally:
    _close_conn(connection)

def get_photos_from_event(event_id):
  query = """
  SELECT * FROM Photo WHERE event_id = %s

  """
  try:
    return _run(query, [event_id])
  except Exception as e:
    print(f"Query Failed: {e}")
    return False

def get_all_photos():
  query = "SELECT id FROM Photo"
  try:
    return _run(query, [])
  except Exception as e:
    print(f"Query Failed: {e}")
    return False


def is_user_in_event_sql(user_id, event_id):
  connection = None
  try:
    connection = get_db()
    if has_deleted_at_column(connection):
      query = """
        SELECT 1
        FROM Participant p
        JOIN Event e ON e.id = p.eventID
        WHERE p.userID = %s AND p.eventID = %s AND e.deleted_at IS NULL
        LIMIT 1
      """
    else:
      query = "SELECT 1 FROM Participant WHERE userID = %s AND eventID = %s LIMIT 1"
    return bool(run_query(connection, query, [user_id, event_id]))
  except Exception as e:
    print(f"Query Failed: {e}")
    return False
  finally:
    if connection:
      try:
        connection.close()
      except Exception:
        pass

def get_photo_event_sql(photo_id):
  query = "SELECT event_id FROM Photo WHERE id = %s LIMIT 1"
  try:
    out = _run(query, [photo_id])
    return out[0]['event_id'] if out else None
  except Exception as e:
    print(f"Query Failed: {e}")
    return None


def get_user_role_sql(user_id):
  query = "SELECT role FROM User WHERE id = %s LIMIT 1"
  try:
    out = _run(query, [user_id])
    return out[0]['role'] if out else None
  except Exception as e:
    print(f"Query Failed: {e}")
    return None

def get_user_profile_sql(user_id):
  query = "SELECT id, name, role FROM User WHERE id = %s LIMIT 1"
  try:
    out = _run(query, [user_id])
    return out[0] if out else None
  except Exception as e:
    print(f"Query Failed: {e}")
    return None


def set_user_password_sql(user_id, password_hash):
  try:
    _run("UPDATE User SET password = %s WHERE id = %s", [password_hash, user_id])
    return True
  except Exception as e:
    print(f"Query Failed: {e}")
    return False

def get_user_password_for_admin_sql(user_id):
  """Look up a user's username, role, and passkey for admin recovery."""
  query = "SELECT id, name, role, password FROM User WHERE id = %s LIMIT 1"
  try:
    out = _run(query, [user_id])
    return out[0] if out else None
  except Exception as e:
    print(f"Query Failed: {e}")
    return False

def set_user_role_sql(user_id, role):
  # Never changes an OWNER account
  query = "UPDATE User SET role = %s WHERE id = %s AND UPPER(role) <> 'OWNER'"
  try:
    return _run(query, [role, user_id])
  except Exception as e:
    print(f"Query Failed: {e}")
    return False

def get_event_sql(event_id):
  connection = None
  try:
    connection = get_db()
    if has_deleted_at_column(connection):
      query = "SELECT id, name FROM Event WHERE id = %s AND deleted_at IS NULL LIMIT 1"
    else:
      query = "SELECT id, name FROM Event WHERE id = %s LIMIT 1"
    out = run_query(connection, query, [event_id])
    return out[0] if out else None
  except Exception as e:
    print(f"Query Failed: {e}")
    return None
  finally:
    if connection:
      try:
        connection.close()
      except Exception:
        pass

def get_next_location_index_sql(event_id):
  query = "SELECT COALESCE(MAX(order_index), 0) + 1 AS next_index FROM Pub WHERE eventID = %s"
  try:
    out = _run(query, [event_id])
    return int(out[0]['next_index']) if out else 1
  except Exception as e:
    print(f"Query Failed: {e}")
    return 1

def reorder_locations_sql(event_id, pub_ids):
  query = "UPDATE Pub SET order_index = %s WHERE id = %s AND eventID = %s"
  connection = None
  try:
    connection = get_db()
    with connection.cursor() as cursor:
      for i, pub_id in enumerate(pub_ids):
        cursor.execute(query, [i + 1, pub_id, event_id])
    connection.commit()
    return True
  except Exception as e:
    print(f"Query Failed: {e}")
    return False
  finally:
    _close_conn(connection)


# ---- Current location of a crawl ----
# The ref moves the crawl from pub to pub; players read it from here.
# Needs: ALTER TABLE Event ADD COLUMN current_pub_id VARCHAR(64) NULL DEFAULT NULL;

def get_current_pub_sql(event_id):
  # Returns {"pub_id": id or None}, or False if the query failed
  query = "SELECT current_pub_id FROM Event WHERE id = %s LIMIT 1"
  try:
    out = _run(query, [event_id])
    return {"pub_id": out[0]['current_pub_id'] if out else None}
  except Exception as e:
    print(f"Query Failed: {e}")
    return False

def set_current_pub_sql(event_id, pub_id):
  # Only accepts a pub that belongs to this event
  query = """
          UPDATE Event SET current_pub_id = %s
          WHERE id = %s
            AND EXISTS (SELECT 1 FROM Pub WHERE id = %s AND eventID = %s)
  """
  try:
    _run(query, [pub_id, event_id, pub_id, event_id])
    return True
  except Exception as e:
    print(f"Query Failed: {e}")
    return False
