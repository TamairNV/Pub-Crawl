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

