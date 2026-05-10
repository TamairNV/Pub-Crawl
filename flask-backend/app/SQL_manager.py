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

def get_all_events():
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
