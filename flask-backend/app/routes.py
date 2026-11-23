import json
import shutil
import threading

import flask
from PIL import Image
from functools import wraps
from flask import Blueprint, render_template, jsonify, request, session, abort
import os
import tempfile
import subprocess
import uuid
from werkzeug.utils import secure_filename
import PIL
from pillow_heif import register_heif_opener

register_heif_opener()
UPLOAD_FOLDER = '/app/static/uploads'

main = Blueprint('main', __name__)
from .SQL_manager import *
from .mini_events_manager import (
  get_wheels_for_event_sql,
  create_wheel_sql,
  delete_wheel_sql,
  add_wheel_item_sql,
  update_wheel_item_sql,
  delete_wheel_item_sql,
  seed_starter_wheel_items_sql,
  get_team_adjustments_sql,
  get_event_tasks_sql,
  assign_player_task_sql,
  assign_random_wheel_task_sql,
  confirm_player_task_sql,
  spin_task_wheel_sql,
  spin_direct_wheel_for_player_sql,
  apply_task_target_sql,
  claim_task_done_sql,
  cancel_player_task_sql,
  get_awards_for_event_sql,
  create_award_sql,
  delete_award_sql,
  seed_default_awards_sql,
  get_awards_settings_sql,
  set_awards_settings_sql,
  cast_award_vote_sql,
  get_award_votes_summary_sql,
)


ADMIN_ROLES = ('admin', 'owner')

def current_role():
  # Read the role from the database each time, so making someone admin (or
  # taking it away) works straight away without them logging in again.
  if 'user_id' not in session:
    return ''
  role = get_user_role_sql(session['user_id'])
  if role is None:
    role = session.get('role', '')
  return str(role).lower()

def is_admin():
  return current_role() in ADMIN_ROLES

def is_owner():
  return current_role() == 'owner'

def can_view_event(event_id):
  return is_admin() or is_user_in_event_sql(session['user_id'], event_id)

def login_required(f):
  @wraps(f)
  def wrapper(*args, **kwargs):
    if 'user_id' not in session:
      return jsonify({"status": "failed", "received": "Not logged in"}), 401
    return f(*args, **kwargs)
  return wrapper

def admin_required(f):
  @wraps(f)
  @login_required
  def wrapper(*args, **kwargs):
    if not is_admin():
      return jsonify({"status": "failed", "received": "Forbidden"}), 403
    return f(*args, **kwargs)
  return wrapper

def owner_required(f):
  @wraps(f)
  @login_required
  def wrapper(*args, **kwargs):
    if not is_owner():
      return jsonify({"status": "failed", "received": "Forbidden"}), 403
    return f(*args, **kwargs)
  return wrapper

@main.route('/api/me')
@login_required
def me():
  profile = get_user_profile_sql(session['user_id'])
  if not profile:
    session.clear()
    return jsonify({"status": "failed", "received": "Not logged in"}), 401
  session['role'] = profile['role']
  return jsonify({"status": "success", "received": profile})

@main.route('/api/manage-users')
@owner_required
def manage_users():
  users = get_all_users_sql() or []
  out = [{"id": u['id'], "name": u['name'], "role": u['role']} for u in users]
  out.sort(key=lambda u: str(u['name']).lower())
  return jsonify({"status": "success", "received": out})

@main.route('/api/set-user-role', methods=['POST'])
@owner_required
def set_user_role():
  data = request.get_json(silent=True) or {}
  role = {'admin': 'ADMIN', 'player': 'player'}.get(str(data.get('role', '')).lower())
  user_id = data.get('user_id')
  if not role or not user_id:
    return jsonify({"status": "failed", "received": "Bad request"}), 400
  if user_id == session['user_id']:
    return jsonify({"status": "failed", "received": "You can't change your own role"}), 400
  out = set_user_role_sql(user_id, role)
  if not out:
    return jsonify({"status": "failed", "received": "Not changed"}), 400
  return jsonify({"status": "success", "received": {"user_id": user_id, "role": role}})

@main.route('/api/BOB')
def index():
  data = "BOB"
  return jsonify(data)

@main.route('/api/get-users')
@admin_required
def get_users():
  all_users = get_all_users_sql()
  print(all_users)
  return jsonify(all_users)


@main.route('/api/reveal-password', methods=['POST'])
@admin_required
def reveal_password():
  data = request.get_json(silent=True) or {}
  user_id = data.get('user_id')
  event_id = data.get('event_id')
  if not user_id:
    return jsonify({"status": "failed", "received": "Bad request"}), 400
  if event_id:
    if not get_event_sql(event_id):
      return jsonify({"status": "failed", "received": "Event not found"}), 404
    if not is_user_in_event_sql(user_id, event_id):
      return jsonify({"status": "failed", "received": "Player is not in this crawl"}), 404

  user_row = get_user_password_for_admin_sql(user_id)
  if user_row is False:
    return jsonify({"status": "failed", "received": "Could not load password"}), 500
  if not user_row:
    return jsonify({"status": "failed", "received": "User not found"}), 404

  if str(user_row.get('role') or '').upper() == 'OWNER' and not is_owner():
    return jsonify({"status": "failed", "received": "Owner passwords cannot be revealed by admins"}), 403

  resp = jsonify({
    "status": "success",
    "received": {
      "id": user_row['id'],
      "name": user_row['name'],
      "password": user_row['password'],
    },
  })
  resp.headers['Cache-Control'] = 'no-store'
  return resp

from flask import send_from_directory

@main.route('/static/uploads/<filename>')
@login_required
def serve_uploaded_media(filename):
  # Only people in the photo's crawl (or admins) can open it
  event_id = get_photo_event_sql(f"static/uploads/{filename}")
  if event_id is None or not can_view_event(event_id):
    return jsonify({"status": "failed", "received": "Not found"}), 404
  return send_from_directory('/app/static/uploads', filename)

@main.route('/static/uploads/thumbs/<filename>')
@login_required
def serve_thumbnail(filename):
  # Small preview of a photo, or a still frame of a video, made on first request
  stem = os.path.splitext(filename)[0]
  for ext in ('.jpg', '.mp4'):
    event_id = get_photo_event_sql(f"static/uploads/{stem}{ext}")
    if event_id is not None:
      break
  if event_id is None or not can_view_event(event_id):
    return jsonify({"status": "failed", "received": "Not found"}), 404
  thumb_name = make_thumbnail(f"{stem}{ext}")
  if not thumb_name:
    return send_from_directory(UPLOAD_FOLDER, f"{stem}{ext}")
  response = send_from_directory(THUMB_FOLDER, thumb_name)
  response.headers['Cache-Control'] = 'private, max-age=604800'
  return response

@main.route('/api/logout-user',methods=['POST'])
def logout_user():
  session.clear()
  return jsonify({"status": "success", "received": "Logged out"})

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
    session.clear()
    session.permanent = True
    session['user_id'] = user[0]['id']
    session['role'] = user[0]['role']
    profile = {"id": user[0]['id'], "name": user[0]['name'], "role": user[0]['role']}
    return jsonify({"status": "success", "received": profile})
  else:
    return jsonify({"status": "failed", "received": "Wrong"})


  return jsonify({"status": "success", "received": user_data})

@main.route('/api/create-crawl',methods=['POST'])
@admin_required
def create_crawl():
  user_data = request.get_json()
  if not user_data:
    return jsonify({"status": "failed", "received": user_data})

  name = str(user_data.get('name', '')).strip()
  if not name:
    return jsonify({"status": "failed", "received": "Name needed"})
  id = user_data.get('id') or str(uuid.uuid4())
  out = create_event_sql(id,name)
  if out:
    return jsonify({"status": "success", "received": out['id']})
  return jsonify({"status": "failed", "received": "Could not create crawl"})


@main.route('/api/get-teams',methods=['GET', 'POST'])
@admin_required
def get_teams():
  data = request.get_json()
  if not data:
    return jsonify({"status": "failed", "received": data})
  print(data)
  teams = get_all_teams_sql(data['event_id'])
  print(teams)
  return jsonify({"status": "success", "received": teams})



@main.route('/api/save-new-team',methods=['GET', 'POST'])
@admin_required
def save_new_team():
  data = request.get_json()
  if not data:
    return jsonify({"status": "failed", "received": data})

  teams = create_new_team_sql(data['name'],data['colour'],data['event_id'])
  return jsonify({"status": "success", "received": teams})


@main.route('/api/save-people-to-event',methods=['GET', 'POST'])
@admin_required
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
@admin_required
def get_events():
  out = get_all_events_sql()
  if out is not False:
    return jsonify({"status": "success", "received": out})
  else:
    return jsonify({"status": "fail", "received": out})


def _remove_event_media_files(photo_paths):
  for photo_path in (photo_paths or []):
    try:
      basename = os.path.basename(photo_path)
      if not basename:
        continue
      media_file = os.path.join(UPLOAD_FOLDER, basename)
      if os.path.exists(media_file):
        os.remove(media_file)
      stem = os.path.splitext(basename)[0]
      thumb_file = os.path.join(THUMB_FOLDER, f"{stem}.jpg")
      if os.path.exists(thumb_file):
        os.remove(thumb_file)
    except Exception as exc:
      print(f"Photo cleanup warning for {photo_path}: {exc}")


@main.route('/api/delete-event', methods=['POST'])
@owner_required
def delete_event():
  data = request.get_json(silent=True) or {}
  event_id = data.get('event_id')
  if not event_id:
    return jsonify({"status": "failed", "received": "Bad request"}), 400

  out = soft_delete_event_sql(event_id)
  if out == 'schema_missing':
    return jsonify({
      "status": "failed",
      "schema_missing": True,
      "received": "Soft-delete migration needed: run migrations/20261114_soft_delete.sql first.",
    }), 503
  if out is None:
    return jsonify({"status": "failed", "received": "Event not found"}), 404
  if out is False:
    return jsonify({"status": "failed", "received": "Could not delete event"}), 500

  return jsonify({"status": "success", "received": event_id})


@main.route('/api/get-deleted-events', methods=['GET'])
@owner_required
def get_deleted_events():
  out = get_deleted_events_sql()
  if out == 'schema_missing':
    return jsonify({
      "status": "failed",
      "schema_missing": True,
      "received": "Soft-delete migration needed: run migrations/20261114_soft_delete.sql first.",
    }), 503
  if out is False:
    return jsonify({"status": "failed", "received": "Could not load deleted events"}), 500
  return jsonify({"status": "success", "received": out})


@main.route('/api/restore-event', methods=['POST'])
@owner_required
def restore_event():
  data = request.get_json(silent=True) or {}
  event_id = data.get('event_id')
  if not event_id:
    return jsonify({"status": "failed", "received": "Bad request"}), 400

  out = restore_event_sql(event_id)
  if out == 'schema_missing':
    return jsonify({
      "status": "failed",
      "schema_missing": True,
      "received": "Soft-delete migration needed: run migrations/20261114_soft_delete.sql first.",
    }), 503
  if out is None:
    return jsonify({"status": "failed", "received": "Deleted event not found"}), 404
  if out is False:
    return jsonify({"status": "failed", "received": "Could not restore event"}), 500
  return jsonify({"status": "success", "received": event_id})


@main.route('/api/purge-event', methods=['POST'])
@owner_required
def purge_event():
  data = request.get_json(silent=True) or {}
  event_id = data.get('event_id')
  if not event_id:
    return jsonify({"status": "failed", "received": "Bad request"}), 400

  out = delete_event_sql(event_id, only_deleted=True)
  if out == 'schema_missing':
    return jsonify({
      "status": "failed",
      "schema_missing": True,
      "received": "Soft-delete migration needed: run migrations/20261114_soft_delete.sql first.",
    }), 503
  if out is None:
    return jsonify({"status": "failed", "received": "Deleted event not found"}), 404
  if out is False:
    return jsonify({"status": "failed", "received": "Could not permanently delete event"}), 500

  _remove_event_media_files(out)
  return jsonify({"status": "success", "received": event_id})


@main.route('/api/reset-event', methods=['POST'])
@owner_required
def reset_event():
  data = request.get_json(silent=True) or {}
  event_id = data.get('event_id')
  if not event_id:
    return jsonify({"status": "failed", "received": "Bad request"}), 400

  clear_media = bool(data.get('clear_media', True))
  out = reset_event_data_sql(event_id, clear_media=clear_media)
  if out is None:
    return jsonify({"status": "failed", "received": "Event not found"}), 404
  if out is False:
    return jsonify({"status": "failed", "received": "Could not reset event scores"}), 500

  if clear_media:
    _remove_event_media_files(out.get('photos'))

  return jsonify({"status": "success", "received": out.get('cleared')})

@main.route('/api/get-event-details',methods=['GET', 'POST'])
def get_event_details():
  data = request.get_json()
  if not data:
    return jsonify({"status": "failed", "received": "failed"})

  event_id = data['event_id']

  people = get_users_in_event_sql(event_id)
  teams = get_teams_in_event_sql(event_id)
  print(people,teams)
  if people is not False and teams is not False:
    event = get_event_sql(event_id)
    response = {'users' : people, "teams" : teams, "event": event}
    return jsonify({"status": "success", "received": response})
  else:

    return jsonify({"status": "failed", "received": "failed"})


@main.route('/api/update-user-team',methods=['GET', 'POST'])
@admin_required
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
@admin_required
def add_new_location():
  data = request.get_json()
  if not data:
    return jsonify({"status": "failed", "received": data})

  name = data['name']
  event_id = data['event_id']
  index = get_next_location_index_sql(event_id)

  out = add_new_location_sql(name,event_id,index)

  if out:
    return jsonify({"status": "success", "received": out['id']})
  else:
    return jsonify({"status": "failed", "received": out})



@main.route('/api/add-new-rule',methods=['GET', 'POST'])
@admin_required
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


@main.route('/api/set-pub-rule', methods=['POST'])
@admin_required
def set_pub_rule():
  data = request.get_json(silent=True) or {}
  pub_id = data.get('pub_id')
  event_id = data.get('event_id')
  name = str(data.get('name', '')).strip()
  description = str(data.get('description', '')).strip()
  if not pub_id or not event_id:
    return jsonify({"status": "failed", "received": "Bad request"}), 400
  if set_pub_rule_sql(pub_id, name, description, event_id):
    return jsonify({"status": "success", "received": pub_id})
  return jsonify({"status": "failed", "received": "Could not update rule"})


@main.route('/api/get-base-rules',methods=['GET', 'POST'])
def get_base_rules():
  data = request.get_json()
  if not data:
    return jsonify({"status": "failed", "received": data})

  event_id = data['event_id']

  out = get_all_base_rules_sql(event_id)
  if out is not False:
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
  if out is not False:
    return jsonify({"status": "success", "received": out})
  else:
    return jsonify({"status": "failed", "received": out})

@main.route('/api/remove-user',methods=['GET', 'POST'])
@admin_required
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
@admin_required
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
@admin_required
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



@main.route('/api/reorder-locations', methods=['POST'])
@admin_required
def reorder_locations():
  data = request.get_json(silent=True) or {}
  event_id = data.get('event_id')
  pub_ids = data.get('pub_ids')
  if not event_id or not isinstance(pub_ids, list):
    return jsonify({"status": "failed", "received": "Bad request"}), 400
  if reorder_locations_sql(event_id, pub_ids):
    return jsonify({"status": "success", "received": len(pub_ids)})
  return jsonify({"status": "failed", "received": "Could not reorder"})


@main.route('/api/get-user-points',methods=['GET', 'POST'])
def get_user_points():
  data = request.get_json()
  if not data:
    return jsonify({"status": "failed", "received": data})

  event_id = data['event_id']

  out = get_user_points_sql(event_id)
  if out is not False:
    return jsonify({"status": "success", "received": out})
  else:
    return jsonify({"status": "failed", "received": out})


@main.route('/api/give-user-points',methods=['GET', 'POST'])
@admin_required
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

@main.route('/api/get-user-events',methods=['GET', 'POST'])
def get_user_events():
  data = request.get_json()
  if not data:
    return jsonify({"status": "failed", "received": data})

  user_id = data['user_id']

  out = events_user_is_in_sql(user_id)
  if out is not False:
    return jsonify({"status": "success", "received": out})
  else:
    return jsonify({"status": "failed", "received": out})

THUMB_FOLDER = os.path.join(UPLOAD_FOLDER, 'thumbs')
THUMB_SIZE = 640

def make_thumbnail(media_name):
  # Returns the thumbnail's file name, creating it if needed; None if it can't be made
  stem, ext = os.path.splitext(media_name)
  thumb_name = f"{stem}.jpg"
  thumb_path = os.path.join(THUMB_FOLDER, thumb_name)
  if os.path.exists(thumb_path):
    return thumb_name
  source = os.path.join(UPLOAD_FOLDER, media_name)
  if not os.path.exists(source):
    return None
  os.makedirs(THUMB_FOLDER, exist_ok=True)
  # Write to a temp name first so two workers can't serve a half-written file
  tmp_path = f"{thumb_path}.{uuid.uuid4().hex}.tmp"
  try:
    if ext.lower() == '.mp4':
      for seek in ('1', '0'):
        subprocess.run(['ffmpeg', '-y', '-ss', seek, '-i', source, '-frames:v', '1',
                        '-vf', f"scale='min({THUMB_SIZE},iw)':-2", '-q:v', '5', '-f', 'mjpeg', tmp_path],
                       capture_output=True)
        if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
          break
    else:
      with Image.open(source) as img:
        img = img.convert('RGB')
        img.thumbnail((THUMB_SIZE, THUMB_SIZE))
        img.save(tmp_path, 'jpeg', quality=70)
    if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
      return None
    os.replace(tmp_path, thumb_path)
    return thumb_name
  except Exception as e:
    print(f"Thumbnail failed for {media_name}: {e}")
    return None

# --- Modified Upload Route ---

@main.route('/api/upload-media', methods=['POST'])
@login_required
def upload_media():
  if 'files' not in request.files:
    return jsonify({"status": "failed", "received": "No file part in the request"}), 400

  files = request.files.getlist('files')
  metadata_raw = request.form.get('metadata')

  if not metadata_raw:
    return jsonify({"status": "failed", "received": "No metadata provided"}), 400

  try:
    metadata = json.loads(metadata_raw)
  except Exception as e:
    return jsonify({"status": "failed", "received": "Invalid metadata JSON"}), 400

  user_id = session['user_id']
  event_id = metadata.get('event_id')
  if not event_id or not can_view_event(event_id):
    return jsonify({"status": "failed", "received": "Forbidden"}), 403
  file_meta_list = metadata.get('files_data', [])

  os.makedirs(UPLOAD_FOLDER, exist_ok=True)

  saved_photos_db_data = []

  for i, file in enumerate(files):
    if file.filename == '':
      continue

    ext = os.path.splitext(file.filename)[1].lower()
    unique_id = str(uuid.uuid4())

    meta = file_meta_list[i] if i < len(file_meta_list) else {}
    time_taken = meta.get('time_taken')
    lat = meta.get('latitude')
    lng = meta.get('longitude')

    if ext in ['.mp4', '.mov', '.avi', '.webm', '.mkv']:
      final_filename = f"{unique_id}.mp4"
      final_filepath = os.path.join(UPLOAD_FOLDER, final_filename)

      if ext == '.mp4':
        file.save(final_filepath)
      else:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_in:
          file.save(temp_in.name)
          temp_in_path = temp_in.name

        try:
          subprocess.run([
            'ffmpeg', '-y', '-i', temp_in_path,
            '-vcodec', 'libx264', '-acodec', 'aac',
            '-movflags', '+faststart',
            final_filepath
          ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
          print(f"FFmpeg conversion failed: {e.stderr.decode('utf-8')}")
          os.remove(temp_in_path)
          continue

        os.remove(temp_in_path)

    else:
      final_filename = f"{unique_id}.jpg"
      final_filepath = os.path.join(UPLOAD_FOLDER, final_filename)
      try:
        img = Image.open(file.stream)
        img = img.convert('RGB')
        img.save(final_filepath, 'jpeg', quality=70)
      except Exception as e:
        print(f"Image conversion failed: {e}")
        continue

    make_thumbnail(final_filename)

    saved_photos_db_data.append({
      'id': f"static/uploads/{final_filename}",
      'time_taken': time_taken,
      'latitude': lat,
      'longitude': lng
    })

  if saved_photos_db_data:
    db_result = save_photo_ids_sql(user_id, event_id, saved_photos_db_data)
    if not db_result:
      return jsonify({"status": "failed", "received": "Database save failed"}), 500

  return jsonify({
    "status": "success",
    "received": f"Successfully uploaded {len(saved_photos_db_data)} files"
  })


@main.route('/api/get-event-photos',methods=['GET', 'POST'])
@login_required
def get_event_photos():
  data = request.get_json()
  if not data:
    return jsonify({"status": "failed", "received": data})
  event_id = data['event_id']
  if not can_view_event(event_id):
    return jsonify({"status": "failed", "received": "Forbidden"}), 403
  out = get_photos_from_event(event_id)
  if out:
    return jsonify({"status": "success", "received": out})
  else:
    return jsonify({"status": "failed", "received": out})


@main.route('/api/get-current-pub', methods=['POST'])
@login_required
def get_current_pub():
  data = request.get_json(silent=True) or {}
  event_id = data.get('event_id')
  if not event_id or not can_view_event(event_id):
    return jsonify({"status": "failed", "received": "failed"}), 403
  out = get_current_pub_sql(event_id)
  if out is False:
    return jsonify({"status": "failed", "received": "failed"})
  return jsonify({"status": "success", "received": out})


@main.route('/api/set-current-pub', methods=['POST'])
@admin_required
def set_current_pub():
  data = request.get_json(silent=True) or {}
  event_id = data.get('event_id')
  pub_id = data.get('pub_id')
  if not event_id or not pub_id:
    return jsonify({"status": "failed", "received": "failed"}), 400
  if not set_current_pub_sql(event_id, pub_id):
    return jsonify({"status": "failed", "received": "failed"})
  return jsonify({"status": "success", "received": {"pub_id": pub_id}})


# ==================== MINI EVENTS: WHEELS, TASKS, AWARDS ====================

@main.route('/api/get-mini-events', methods=['POST'])
@login_required
def get_mini_events():
  data = request.get_json(silent=True) or {}
  event_id = data.get('event_id')
  if not event_id or not can_view_event(event_id):
    return jsonify({"status": "failed", "received": "Forbidden"}), 403

  wheels = get_wheels_for_event_sql(event_id)
  awards = get_awards_for_event_sql(event_id)
  settings = get_awards_settings_sql(event_id)
  admin_user = is_admin()
  votes = get_award_votes_summary_sql(
    event_id,
    session['user_id'],
    include_tally=admin_user or settings['results_visible'],
    include_all_voters=admin_user,
  )
  team_adjustments = get_team_adjustments_sql(event_id)
  if wheels is False or awards is False or votes is False or team_adjustments is False:
    return jsonify({"status": "failed", "received": "Could not load mini events"}), 500

  return jsonify({
    "status": "success",
    "received": {
      "wheels": wheels,
      "awards": awards,
      "awards_settings": settings,
      "awards_votes": votes,
      "team_adjustments": team_adjustments,
    },
  })


@main.route('/api/player-live-state', methods=['POST'])
@login_required
def player_live_state():
  data = request.get_json(silent=True) or {}
  event_id = data.get('event_id')
  if not event_id or not can_view_event(event_id):
    return jsonify({"status": "failed", "received": "Forbidden"}), 403

  cur_pub = get_current_pub_sql(event_id)
  my_tasks = get_event_tasks_sql(event_id, user_id=session['user_id'])
  points = get_user_points_sql(event_id)
  team_adjustments = get_team_adjustments_sql(event_id)
  wheels = get_wheels_for_event_sql(event_id)
  awards = get_awards_for_event_sql(event_id)
  settings = get_awards_settings_sql(event_id)
  admin_user = is_admin()
  votes = get_award_votes_summary_sql(
    event_id,
    session['user_id'],
    include_tally=admin_user or settings['results_visible'],
    include_all_voters=False,
  )
  if (
    cur_pub is False
    or my_tasks is False
    or points is False
    or team_adjustments is False
    or wheels is False
    or awards is False
    or votes is False
  ):
    return jsonify({"status": "failed", "received": "Could not fetch live state"}), 500

  return jsonify({
    "status": "success",
    "received": {
      "current_pub_id": cur_pub.get('pub_id'),
      "my_tasks": my_tasks,
      "points": points,
      "team_adjustments": team_adjustments,
      "wheels": wheels,
      "awards": awards,
      "awards_settings": settings,
      "awards_votes": votes,
    },
  })


@main.route('/api/ref-live-state', methods=['POST'])
@admin_required
def ref_live_state():
  data = request.get_json(silent=True) or {}
  event_id = data.get('event_id')
  if not event_id:
    return jsonify({"status": "failed", "received": "Bad request"}), 400

  tasks = get_event_tasks_sql(event_id)
  wheels = get_wheels_for_event_sql(event_id)
  points = get_user_points_sql(event_id)
  team_adjustments = get_team_adjustments_sql(event_id)
  awards = get_awards_for_event_sql(event_id)
  settings = get_awards_settings_sql(event_id)
  votes = get_award_votes_summary_sql(
    event_id,
    session['user_id'],
    include_tally=True,
    include_all_voters=True,
  )
  if (
    tasks is False
    or wheels is False
    or points is False
    or team_adjustments is False
    or awards is False
    or votes is False
  ):
    return jsonify({"status": "failed", "received": "Could not fetch ref live state"}), 500

  return jsonify({
    "status": "success",
    "received": {
      "tasks": tasks,
      "wheels": wheels,
      "points": points,
      "team_adjustments": team_adjustments,
      "awards": awards,
      "awards_settings": settings,
      "awards_votes": votes,
    },
  })


@main.route('/api/create-wheel', methods=['POST'])
@admin_required
def create_wheel():
  data = request.get_json(silent=True) or {}
  event_id = data.get('event_id')
  name = str(data.get('name', '')).strip()
  description = str(data.get('description', '')).strip()
  if not event_id or not name:
    return jsonify({"status": "failed", "received": "Bad request"}), 400
  out = create_wheel_sql(event_id, name, description)
  if out:
    return jsonify({"status": "success", "received": out})
  return jsonify({"status": "failed", "received": "Could not create wheel"})


@main.route('/api/delete-wheel', methods=['POST'])
@admin_required
def delete_wheel():
  data = request.get_json(silent=True) or {}
  event_id = data.get('event_id')
  wheel_id = data.get('wheel_id')
  if not event_id or not wheel_id:
    return jsonify({"status": "failed", "received": "Bad request"}), 400
  if delete_wheel_sql(wheel_id, event_id):
    return jsonify({"status": "success", "received": wheel_id})
  return jsonify({"status": "failed", "received": "Could not delete wheel"})


@main.route('/api/add-wheel-item', methods=['POST'])
@admin_required
def add_wheel_item():
  data = request.get_json(silent=True) or {}
  event_id = data.get('event_id')
  wheel_id = data.get('wheel_id')
  label = str(data.get('label', '')).strip()
  if not event_id or not wheel_id or not label:
    return jsonify({"status": "failed", "received": "Bad request"}), 400
  out = add_wheel_item_sql(
    wheel_id=wheel_id,
    event_id=event_id,
    label=label,
    description=str(data.get('description', '')).strip(),
    requires_completion=bool(data.get('requires_completion', True)),
    effect_type=str(data.get('effect_type', 'add_points')),
    points=data.get('points', 1),
    colour=data.get('colour'),
  )
  if out:
    return jsonify({"status": "success", "received": out})
  return jsonify({"status": "failed", "received": "Could not add item"})


@main.route('/api/update-wheel-item', methods=['POST'])
@admin_required
def update_wheel_item():
  data = request.get_json(silent=True) or {}
  event_id = data.get('event_id')
  item_id = data.get('item_id')
  label = str(data.get('label', '')).strip()
  if not event_id or not item_id or not label:
    return jsonify({"status": "failed", "received": "Bad request"}), 400
  ok = update_wheel_item_sql(
    item_id=item_id,
    event_id=event_id,
    label=label,
    description=str(data.get('description', '')).strip(),
    requires_completion=bool(data.get('requires_completion', True)),
    effect_type=str(data.get('effect_type', 'add_points')),
    points=data.get('points', 1),
    colour=data.get('colour', '#fbbf24'),
  )
  if ok:
    return jsonify({"status": "success", "received": item_id})
  return jsonify({"status": "failed", "received": "Could not update item"})


@main.route('/api/delete-wheel-item', methods=['POST'])
@admin_required
def delete_wheel_item():
  data = request.get_json(silent=True) or {}
  event_id = data.get('event_id')
  item_id = data.get('item_id')
  if not event_id or not item_id:
    return jsonify({"status": "failed", "received": "Bad request"}), 400
  if delete_wheel_item_sql(item_id, event_id):
    return jsonify({"status": "success", "received": item_id})
  return jsonify({"status": "failed", "received": "Could not delete item"})


@main.route('/api/seed-wheel-items', methods=['POST'])
@admin_required
def seed_wheel_items():
  data = request.get_json(silent=True) or {}
  event_id = data.get('event_id')
  wheel_id = data.get('wheel_id')
  if not event_id or not wheel_id:
    return jsonify({"status": "failed", "received": "Bad request"}), 400
  out = seed_starter_wheel_items_sql(wheel_id, event_id)
  if out is False:
    return jsonify({"status": "failed", "received": "Could not add starter wheel tasks"})
  return jsonify({"status": "success", "received": out})


@main.route('/api/assign-player-task', methods=['POST'])
@admin_required
def assign_player_task():
  data = request.get_json(silent=True) or {}
  event_id = data.get('event_id')
  user_id = data.get('user_id')
  mode = str(data.get('mode', 'custom')).strip().lower()
  if not event_id or not user_id:
    return jsonify({"status": "failed", "received": "Bad request"}), 400

  if mode == 'random':
    out = assign_random_wheel_task_sql(
      event_id=event_id,
      user_id=user_id,
      assigned_by=session['user_id'],
      wheel_id=data.get('wheel_id') or None,
      override_reward_wheel_id=data.get('reward_wheel_id') or None,
    )
    if out is None:
      return jsonify({"status": "failed", "received": "That wheel has no tasks yet"}), 400
    if out:
      return jsonify({"status": "success", "received": out})
    return jsonify({"status": "failed", "received": "Could not assign random task"})

  title = str(data.get('title', '')).strip()
  if not title:
    return jsonify({"status": "failed", "received": "Task title required"}), 400

  out = assign_player_task_sql(
    event_id=event_id,
    user_id=user_id,
    assigned_by=session['user_id'],
    title=title,
    description=str(data.get('description', '')).strip(),
    wheel_id=data.get('wheel_id') or None,
    wheel_item_id=data.get('wheel_item_id') or None,
    reward_type=str(data.get('reward_type', 'add_points')),
    reward_points=data.get('reward_points', 1),
    reward_wheel_id=data.get('reward_wheel_id') or None,
  )
  if out:
    return jsonify({"status": "success", "received": out})
  return jsonify({"status": "failed", "received": "Could not assign task"})


@main.route('/api/spin-direct-wheel', methods=['POST'])
@admin_required
def spin_direct_wheel():
  data = request.get_json(silent=True) or {}
  event_id = data.get('event_id')
  user_id = data.get('user_id')
  wheel_id = data.get('wheel_id')
  if not event_id or not user_id or not wheel_id:
    return jsonify({"status": "failed", "received": "Bad request"}), 400
  out = spin_direct_wheel_for_player_sql(event_id, user_id, session['user_id'], wheel_id)
  if out == 'empty_wheel':
    return jsonify({"status": "failed", "received": "Add at least one item to this wheel first"}), 400
  if not out:
    return jsonify({"status": "failed", "received": "Could not spin wheel"})
  return jsonify({"status": "success", "received": out})


@main.route('/api/confirm-player-task', methods=['POST'])
@admin_required
def confirm_player_task():
  data = request.get_json(silent=True) or {}
  event_id = data.get('event_id')
  task_id = data.get('task_id')
  if not event_id or not task_id:
    return jsonify({"status": "failed", "received": "Bad request"}), 400
  out = confirm_player_task_sql(
    task_id=task_id,
    event_id=event_id,
    ref_id=session['user_id'],
    target_team_id=data.get('target_team_id') or None,
  )
  if out is None:
    return jsonify({"status": "failed", "received": "Task not found"}), 404
  if out is False:
    return jsonify({"status": "failed", "received": "Could not confirm task"})
  return jsonify({"status": "success", "received": out})


@main.route('/api/cancel-player-task', methods=['POST'])
@admin_required
def cancel_player_task():
  data = request.get_json(silent=True) or {}
  event_id = data.get('event_id')
  task_id = data.get('task_id')
  if not event_id or not task_id:
    return jsonify({"status": "failed", "received": "Bad request"}), 400
  if cancel_player_task_sql(task_id, event_id):
    return jsonify({"status": "success", "received": task_id})
  return jsonify({"status": "failed", "received": "Could not cancel task"})


@main.route('/api/claim-task-done', methods=['POST'])
@login_required
def claim_task_done():
  data = request.get_json(silent=True) or {}
  event_id = data.get('event_id')
  task_id = data.get('task_id')
  if not event_id or not task_id:
    return jsonify({"status": "failed", "received": "Bad request"}), 400
  out = claim_task_done_sql(task_id, event_id, session['user_id'])
  if out:
    return jsonify({"status": "success", "received": out})
  return jsonify({"status": "failed", "received": "Could not update task"})


@main.route('/api/spin-task-wheel', methods=['POST'])
@login_required
def spin_task_wheel():
  data = request.get_json(silent=True) or {}
  event_id = data.get('event_id')
  task_id = data.get('task_id')
  if not event_id or not task_id:
    return jsonify({"status": "failed", "received": "Bad request"}), 400
  out = spin_task_wheel_sql(task_id, event_id, session['user_id'], is_admin())
  if out == 'forbidden':
    return jsonify({"status": "failed", "received": "Forbidden"}), 403
  if out == 'empty_wheel':
    return jsonify({"status": "failed", "received": "This wheel has no items yet"}), 400
  if out is None:
    return jsonify({"status": "failed", "received": "Task not found"}), 404
  if out is False:
    return jsonify({"status": "failed", "received": "Could not spin wheel"})
  return jsonify({"status": "success", "received": out})


@main.route('/api/apply-task-target', methods=['POST'])
@login_required
def apply_task_target():
  data = request.get_json(silent=True) or {}
  event_id = data.get('event_id')
  task_id = data.get('task_id')
  target_team_id = data.get('target_team_id')
  if not event_id or not task_id or not target_team_id:
    return jsonify({"status": "failed", "received": "Bad request"}), 400
  out = apply_task_target_sql(task_id, event_id, target_team_id, session['user_id'], is_admin())
  if out == 'forbidden':
    return jsonify({"status": "failed", "received": "Forbidden"}), 403
  if out == 'invalid_team':
    return jsonify({"status": "failed", "received": "Invalid target team"}), 400
  if out is None:
    return jsonify({"status": "failed", "received": "Task not found"}), 404
  if out is False:
    return jsonify({"status": "failed", "received": "Could not apply team points"})
  return jsonify({"status": "success", "received": out})


@main.route('/api/create-award', methods=['POST'])
@admin_required
def create_award():
  data = request.get_json(silent=True) or {}
  event_id = data.get('event_id')
  name = str(data.get('name', '')).strip()
  description = str(data.get('description', '')).strip()
  target_type = str(data.get('target_type', 'player')).strip().lower()
  if not event_id or not name:
    return jsonify({"status": "failed", "received": "Bad request"}), 400
  out = create_award_sql(event_id, name, description, target_type)
  if out:
    return jsonify({"status": "success", "received": out})
  return jsonify({"status": "failed", "received": "Could not create award"})


@main.route('/api/delete-award', methods=['POST'])
@admin_required
def delete_award():
  data = request.get_json(silent=True) or {}
  event_id = data.get('event_id')
  award_id = data.get('award_id')
  if not event_id or not award_id:
    return jsonify({"status": "failed", "received": "Bad request"}), 400
  if delete_award_sql(award_id, event_id):
    return jsonify({"status": "success", "received": award_id})
  return jsonify({"status": "failed", "received": "Could not delete award"})


@main.route('/api/seed-default-awards', methods=['POST'])
@admin_required
def seed_default_awards():
  data = request.get_json(silent=True) or {}
  event_id = data.get('event_id')
  if not event_id:
    return jsonify({"status": "failed", "received": "Bad request"}), 400
  out = seed_default_awards_sql(event_id)
  if out is False:
    return jsonify({"status": "failed", "received": "Could not add default awards"})
  return jsonify({"status": "success", "received": out})


@main.route('/api/set-awards-settings', methods=['POST'])
@admin_required
def set_awards_settings():
  data = request.get_json(silent=True) or {}
  event_id = data.get('event_id')
  if not event_id:
    return jsonify({"status": "failed", "received": "Bad request"}), 400
  out = set_awards_settings_sql(
    event_id,
    voting_open=data.get('voting_open') if 'voting_open' in data else None,
    results_visible=data.get('results_visible') if 'results_visible' in data else None,
  )
  if out is False:
    return jsonify({"status": "failed", "received": "Could not update award settings"})
  return jsonify({"status": "success", "received": out})


@main.route('/api/cast-award-vote', methods=['POST'])
@login_required
def cast_award_vote():
  data = request.get_json(silent=True) or {}
  event_id = data.get('event_id')
  award_id = data.get('award_id')
  nominee_id = data.get('nominee_id')
  nominee_type = str(data.get('nominee_type', 'player')).strip().lower()
  voter_user_id = data.get('voter_user_id') or session['user_id']

  if not event_id or not award_id or not nominee_id:
    return jsonify({"status": "failed", "received": "Bad request"}), 400

  admin_user = is_admin()
  if voter_user_id != session['user_id'] and not admin_user:
    return jsonify({"status": "failed", "received": "Forbidden"}), 403
  if not can_view_event(event_id):
    return jsonify({"status": "failed", "received": "Forbidden"}), 403

  out = cast_award_vote_sql(
    event_id=event_id,
    award_id=award_id,
    voter_user_id=voter_user_id,
    nominee_id=nominee_id,
    nominee_type=nominee_type,
    cast_by_user_id=session['user_id'],
    actor_is_admin=admin_user,
  )
  if out == 'voting_closed':
    return jsonify({"status": "failed", "received": "Voting is currently closed"}), 403
  if out in ('bad_request', 'invalid_nominee', 'invalid_voter'):
    return jsonify({"status": "failed", "received": "Invalid vote selection"}), 400
  if out == 'not_found':
    return jsonify({"status": "failed", "received": "Award not found"}), 404
  if out is not True:
    return jsonify({"status": "failed", "received": "Could not save vote"})
  return jsonify({"status": "success", "received": {"award_id": award_id, "voter_user_id": voter_user_id}})
