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

import uuid

import uuid
import json
from datetime import datetime


def get_all_users_sql():
  query = "SELECT * FROM User"
  try:
    connection = get_db()
    params = []
    return run_query(connection, query, params)

  except Exception as e:
    print(f"Query Failed: {e}")
    return False

def select_users_sql(user_ids):
  format_strings = ','.join(['%s'] * len(user_ids))
  query = f"SELECT * FROM users WHERE id IN ({format_strings})"
  try:
    connection = get_db()
    params = [id]
    return run_query(connection, query, params)

  except Exception as e:
    print(f"Query Failed: {e}")
    return False

def is_name_taken(name):
  query = "SELECT * FROM User WHERE name = %s LIMIT 1"
  try:
    connection = get_db()
    params = [name]
    results = run_query(connection, query, params)

    return bool(results)

  except Exception as e:
    print(f"Query Failed: {e}")
    return False

  except Exception as e:
    print(f"Query Failed: {e}")
    return False
def create_user_sql(name,passkey,role = "player"):
  query = "INSERT INTO User (name,password,role) VALUES (%s,%s,%s)"

  try:
    connection = get_db()
    params = [name,passkey,role]
    run_query(connection, query, params)
    return True

  except Exception as e:
    print(f"Query Failed: {e}")
    return False



def get_user_data_from_name_sql(name):
  query = "SELECT * FROM User WHERE name = %s LIMIT 1"
  try:
    connection = get_db()
    params = [name]
    return run_query(connection, query, params)

  except Exception as e:
    print(f"Query Failed: {e}")
    return False


def create_event_sql(id,name):
  query = "INSERT INTO Event (id,name) VALUES (%s,%s)"

  try:
    connection = get_db()
    params = [id,name]
    out = run_query(connection, query, params)
    return {
      "id": str(id),
      "out": out
    }

  except Exception as e:
    print(f"Query Failed: {e}")
    return False

def get_all_events_sql():
  query = "SELECT * FROM Event"

  try:
    connection = get_db()
    params = []
    return run_query(connection, query, params)

  except Exception as e:
    print(f"Query Failed: {e}")
    return False

def get_all_teams_sql(eventID):
  query = "SELECT * FROM Team WHERE eventID = %s;"

  try:
    connection = get_db()
    params = [eventID]
    return run_query(connection, query, params)

  except Exception as e:
    print(f"Query Failed: {e}")
    return False

def create_new_team_sql(team_name,team_colour,event_id):
  query = "INSERT INTO Team (id,name,colour,eventID) VALUES (%s,%s,%s,%s)"
  id = uuid.uuid1()

  try:
    connection = get_db()
    params = [id,team_name,team_colour,event_id]
    out = run_query(connection, query, params)

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

  try:
    connection = get_db()
    cursor = connection.cursor()
    cursor.executemany(query, params)
    connection.commit()
    return True

  except Exception as e:
    print(f"Query Failed: {e}")
    return False


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
      connection = get_db()
      params = [event_id]
      return run_query(connection, query, params)

    except Exception as e:
      print(f"Query Failed: {e}")
      return False

def get_teams_in_event_sql(event_id):
  query = "SELECT * FROM Team WHERE eventID = %s;"
  try:
    connection = get_db()
    params = [event_id]
    return run_query(connection, query, params)

  except Exception as e:
    print(f"Query Failed: {e}")
    return False

def update_user_team_sql(event_id,user_id,new_team_id):
  query = "UPDATE Participant SET teamID = %s WHERE userID = %s and eventID = %s"
  try:
    connection = get_db()
    params = [new_team_id,user_id,event_id]
    return run_query(connection, query, params)

  except Exception as e:
    print(f"Query Failed: {e}")
    return False

def add_new_location_sql(name,event_id,index):
  id = str(uuid.uuid1())
  query = "INSERT INTO Pub (id,eventID,name,order_index) VALUES (%s,%s,%s,%s)"
  try:
    connection = get_db()
    params = [id,event_id,name,index]
    out = run_query(connection, query, params)
    return {
      "id": id,
      "out": out
    }

  except Exception as e:
    print(f"Query Failed: {e}")
    return False


def add_new_rule_sql(pub_id,name,description,event_id):
  query = "INSERT INTO Rule (pubID,name,description,event_id) VALUES (%s,%s,%s,%s)"
  try:
    connection = get_db()
    params = [pub_id,name,description,event_id]
    return run_query(connection, query, params)

  except Exception as e:
    print(f"Query Failed: {e}")
    return False

def get_all_base_rules_sql(event_id):
  query = "SELECT * FROM Rule WHERE event_id = %s and pubID IS NULL"
  try:
    connection = get_db()
    params = [event_id]
    return run_query(connection, query, params)

  except Exception as e:
    print(f"Query Failed: {e}")
    return False

def get_location_rules_sql(event_id):
  query = """
          SELECT
            r.name as ruleName,
            r.description as ruleDescription,
            p.name as pubName,
            p.order_index,
            p.id
          FROM Rule as r
                 JOIN Pub as p on r.pubID = p.id
          WHERE p.eventID = %s
          ORDER BY p.order_index ASC;
          """
  try:
    connection = get_db()
    params = [event_id]
    return run_query(connection, query, params)

  except Exception as e:
    print(f"Query Failed: {e}")
    return False

def remove_user_sql(event_id,user_id):
  query = "DELETE FROM Participant WHERE eventID = %s and userID = %s"
  try:
    connection = get_db()
    params = [event_id,user_id]
    return run_query(connection, query, params)

  except Exception as e:
    print(f"Query Failed: {e}")
    return False



def remove_base_rule_sql(rule_id):
  query = "DELETE FROM Rule WHERE id = %s"
  try:
    connection = get_db()
    params = [rule_id]
    return run_query(connection, query, params)

  except Exception as e:
    print(f"Query Failed: {e}")
    return False

def remove_location_sql(pub_id):
  query = "DELETE FROM Rule WHERE pubID = %s"
  connection = get_db()
  params = [pub_id]
  try:
    out = run_query(connection, query, params)

  except Exception as e:
    print(f"Query Failed: {e}")
    return False

  query2 = "DELETE FROM Pub WHERE id = %s;"
  try:
    out2 = run_query(connection, query2, params)

  except Exception as e:
    print(f"Query Failed: {e}")
    return False

  return [out,out2]

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
    connection = get_db()
    params = [event_id]
    return run_query(connection, query, params)

  except Exception as e:
    print(f"Query Failed: {e}")
    return False


def give_user_points_sql(event_id,user_id,points,admin_id):
  query = "INSERT INTO Point (eventID,refID,userID,point_number) VALUES (%s,%s,%s,%s)"
  try:
    connection = get_db()
    params = [event_id,admin_id,user_id,points]
    return run_query(connection, query, params)

  except Exception as e:
    print(f"Query Failed: {e}")
    return False


def events_user_is_in_sql(user_id):
  query = """
        SELECT *
        FROM Participant p
               JOIN Event e ON e.id = p.eventID
        WHERE p.userID = %s;
  """

  try:
    connection = get_db()
    params = [user_id]
    return run_query(connection, query, params)

  except Exception as e:
    print(f"Query Failed: {e}")
    return False


def save_photo_ids_sql(user_id,event_id,photos):
  query = """
  INSERT INTO Photo (id, user_id,event_id,time_taken,latitude,longitude) VALUES(%s,%s,%s,%s,%s,%s)
  """

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

def get_photos_from_event(event_id):
  query = """
  SELECT * FROM Photo WHERE event_id = %s

  """

  try:
    connection = get_db()
    params = [event_id]
    return run_query(connection, query, params)

  except Exception as e:
    print(f"Query Failed: {e}")
    return False

