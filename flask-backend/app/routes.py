import flask
from flask import Blueprint, render_template, jsonify, request


main = Blueprint('main', __name__)
from .SQL_manager import *
@main.route('/api/BOB')
def index():
  data = "BOB"
  return jsonify(data)

@main.route('/api/get-users')
def get_users():
  all_users = get_all_users_sql()
  print(all_users)
  return jsonify(all_users)



@main.route('/api/create-user',methods=['POST'])
def create_user():
  user_data = request.get_json()
  if not user_data:
    return jsonify({"status": "failed", "received": user_data})
  out = is_name_taken(user_data['name'])
  if not out:
    create_user_sql(user_data['name'],user_data['passkey'])
  else:
    return jsonify({"status": "failed", "received": "Taken"})

  return jsonify({"status": "success", "received": user_data})


@main.route('/api/login-user',methods=['POST'])
def login_user():
  user_data = request.get_json()
  if not user_data:
    return jsonify({"status": "failed", "received": user_data})

  user = get_user_data_from_name_sql(user_data['name'])

  if not user:
    print(user)
    return jsonify({"status": "failed", "received": "Wrong"})

  if user[0]['password'] == user_data['passkey']:
    return jsonify({"status": "success", "received": user[0]})
  else:
    return jsonify({"status": "failed", "received": "Wrong"})


  return jsonify({"status": "success", "received": user_data})

@main.route('/api/create-crawl',methods=['POST'])
def create_crawl():
  user_data = request.get_json()
  if not user_data:
    return jsonify({"status": "failed", "received": user_data})

  name = user_data['name']
  id = user_data['id']
  out = create_event_sql(id,name)
  if out:
    return jsonify({"status": "success", "received": out['id']})


@main.route('/api/get-teams',methods=['GET', 'POST'])
def get_teams():
  data = request.get_json()
  if not data:
    return jsonify({"status": "failed", "received": data})
  print(data)
  teams = get_all_teams_sql(data['event_id'])
  print(teams)
  return jsonify({"status": "success", "received": teams})



@main.route('/api/save-new-team',methods=['GET', 'POST'])
def save_new_team():
  data = request.get_json()
  if not data:
    return jsonify({"status": "failed", "received": data})

  teams = create_new_team_sql(data['name'],data['colour'],data['event_id'])
  return jsonify({"status": "success", "received": teams})


@main.route('/api/save-people-to-event',methods=['GET', 'POST'])
def save_people_to_event():
  data = request.get_json()
  if not data:
    return jsonify({"status": "failed", "received": data})

  out = create_participants(data)
  if out:
    return jsonify({"status": "success", "received": out})

  else:
    return jsonify({"status": "fail", "received": out})

@main.route('/api/get-events',methods=['GET', 'POST'])
def get_events():
  out = get_all_events_sql()
  if out:
    return jsonify({"status": "success", "received": out})
  else:
    return jsonify({"status": "fail", "received": out})

@main.route('/api/get-event-details',methods=['GET', 'POST'])
def get_event_details():
  data = request.get_json()
  if not data:
    return jsonify({"status": "failed", "received": data})

  event_id = data['event_id']

  people = get_users_in_event_sql(event_id)
  teams = get_teams_in_event_sql(event_id)

  if teams and people:
    response = {'users' : people, "teams" : teams}
    return jsonify({"status": "success", "received": response})
  else:
    return jsonify({"status": "failed", "received": [people,teams]})


@main.route('/api/update-user-team',methods=['GET', 'POST'])
def update_user_team():
  data = request.get_json()
  if not data:
    return jsonify({"status": "failed", "received": data})

  event_id = data['event_id']
  user_id = data['user_id']
  new_team_id = data['new_team_id']
  out = update_user_team_sql(event_id,user_id,new_team_id)

  if out:
    return jsonify({"status": "success", "received": out})
  else:
    return jsonify({"status": "failed", "received": out})


@main.route('/api/add-new-location',methods=['GET', 'POST'])
def add_new_location():
  data = request.get_json()
  if not data:
    return jsonify({"status": "failed", "received": data})

  name = data['name']
  index = data['index']
  event_id = data['event_id']

  out = add_new_location_sql(name,event_id,index)

  if out:
    return jsonify({"status": "success", "received": out['id']})
  else:
    return jsonify({"status": "failed", "received": out})



@main.route('/api/add-new-rule',methods=['GET', 'POST'])
def add_new_rule():
  data = request.get_json()
  if not data:
    return jsonify({"status": "failed", "received": data})

  name = data['name']
  description = data['description']
  pub_id = data['pub_id']
  event_id = data['event_id']

  out = add_new_rule_sql(pub_id,name,description,event_id)

  if out:
    return jsonify({"status": "success", "received": out})
  else:
    return jsonify({"status": "failed", "received": out})

@main.route('/api/get-base-rules',methods=['GET', 'POST'])
def get_base_rules():
  data = request.get_json()
  if not data:
    return jsonify({"status": "failed", "received": data})

  event_id = data['event_id']

  out = get_all_base_rules_sql(event_id)
  if out:
    return jsonify({"status": "success", "received": out})
  else:
    return jsonify({"status": "failed", "received": out})


@main.route('/api/get-locations-rules',methods=['GET', 'POST'])
def get_locations_rules():
  data = request.get_json()
  if not data:
    return jsonify({"status": "failed", "received": data})

  event_id = data['event_id']

  out = get_location_rules_sql(event_id)
  if out:
    return jsonify({"status": "success", "received": out})
  else:
    return jsonify({"status": "failed", "received": out})

@main.route('/api/remove-user',methods=['GET', 'POST'])
def remove_user_from_event():
  data = request.get_json()
  if not data:
    return jsonify({"status": "failed", "received": data})
  event_id = data['event_id']
  user_id = data['user_id']
  out = remove_user_sql(event_id,user_id)
  if out:
    return jsonify({"status": "success", "received": out})
  else:
    return jsonify({"status": "failed", "received": out})


@main.route('/api/remove-base-rule',methods=['GET', 'POST'])
def remove_base_rule():
  data = request.get_json()
  if not data:
    return jsonify({"status": "failed", "received": data})

  rule_id = data['rule_id']

  out = remove_base_rule_sql(rule_id)
  if out:
    return jsonify({"status": "success", "received": out})
  else:
    return jsonify({"status": "failed", "received": out})

@main.route('/api/remove-location',methods=['GET', 'POST'])
def remove_location():
  data = request.get_json()
  if not data:
    return jsonify({"status": "failed", "received": data})

  pub_id = data['pub_id']

  out = remove_location_sql(pub_id)
  if out:
    return jsonify({"status": "success", "received": out})
  else:
    return jsonify({"status": "failed", "received": out})



@main.route('/api/get-user-points',methods=['GET', 'POST'])
def get_user_points():
  data = request.get_json()
  if not data:
    return jsonify({"status": "failed", "received": data})

  event_id = data['event_id']

  out = get_user_points_sql(event_id)
  if out:
    return jsonify({"status": "success", "received": out})
  else:
    return jsonify({"status": "failed", "received": out})


@main.route('/api/give-user-points',methods=['GET', 'POST'])
def give_user_points():
  data = request.get_json()
  if not data:
    return jsonify({"status": "failed", "received": data})

  event_id = data['event_id']
  user_id = data['user_id']
  ref_id = data['ref_id']
  points = data['points']

  out = give_user_points_sql(event_id,user_id,points,ref_id)
  if out:
    return jsonify({"status": "success", "received": out})
  else:
    return jsonify({"status": "failed", "received": out})
