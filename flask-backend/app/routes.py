import flask
from PIL import Image
from flask import Blueprint, render_template, jsonify, request
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
@main.route('/api/BOB')
def index():
  data = "BOB"
  return jsonify(data)

@main.route('/api/get-users')
def get_users():
  all_users = get_all_users_sql()
  print(all_users)
  return jsonify(all_users)

from flask import send_from_directory

@main.route('/static/uploads/<filename>')
def serve_uploaded_media(filename):
  # This tells Flask exactly where to fetch the files we just saved
  return send_from_directory('/app/static/uploads', filename)

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

@main.route('/api/get-user-events',methods=['GET', 'POST'])
def get_user_events():
  data = request.get_json()
  if not data:
    return jsonify({"status": "failed", "received": data})

  user_id = data['user_id']

  out = events_user_is_in_sql(user_id)
  if out:
    return jsonify({"status": "success", "received": out})
  else:
    return jsonify({"status": "failed", "received": out})

def process_image(raw_path, final_path):
  with Image.open(raw_path) as img:
    if img.mode in ("RGBA", "P"):
      img = img.convert("RGB")
    img.save(final_path, "jpeg", quality=85)
def process_video(raw_path, final_path):
    cmd = [
      'ffmpeg', '-y', '-i', raw_path,
      '-vcodec', 'libx264', '-vf', 'scale=-2:1080','-crf', '23',
      '-preset', 'fast', '-acodec', 'aac',
      final_path
    ]
    subprocess.run(cmd, capture_output=True, check=True)
import os
import json
import tempfile
import subprocess
from flask import Flask, request, jsonify

TEMP_FOLDER = './temp_chunks'

@main.route('/api/upload-footage', methods=['POST'])
def upload_footage():
  file_chunk = request.files.get('file_chunk')
  chunk_index = int(request.form.get('chunk_index', 0))
  total_chunks = int(request.form.get('total_chunks', 1))
  file_id = request.form.get('file_uuid') # Maps to your old file_id
  original_name = request.form.get('original_name')

  # User and Event objects/IDs passed from frontend form data
  user_id_data = request.form.get('user_id')
  event_id = request.form.get('event_id')

  # Parse user_id if it was passed as a JSON string/object
  try:
    user_id = json.loads(user_id_data) if user_id_data.startswith('{') else {"id": user_id_data}
  except Exception:
    user_id = {"id": user_id_data}

  if not file_chunk:
    return jsonify({"error": "No file chunk provided"}), 400

  # 2. Create directory for this specific file's assembly
  file_temp_dir = os.path.join(TEMP_FOLDER, file_id)
  os.makedirs(file_temp_dir, exist_ok=True)

  # 3. Save the current piece
  chunk_path = os.path.join(file_temp_dir, f"chunk_{chunk_index}")
  file_chunk.save(chunk_path)

  # 4. Check if all pieces have landed
  if len(os.listdir(file_temp_dir)) == total_chunks:
    processed_files = []

    # Use a temporary file to hold the reconstructed raw file
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
      temp_raw_path = temp_file.name

    try:
      # Stitch chunks together into the single raw file
      with open(temp_raw_path, 'wb') as target_file:
        for i in range(total_chunks):
          single_chunk_path = os.path.join(file_temp_dir, f"chunk_{i}")
          with open(single_chunk_path, 'rb') as source_chunk:
            target_file.write(source_chunk.read())
          os.remove(single_chunk_path) # Clean up individual fragment immediately
      os.rmdir(file_temp_dir) # Clean up the folder shell

      # --- YOUR EXACT PROCESSING LOGIC BEGINS HERE ---
      exif_result = subprocess.run(
        ['exiftool', '-j', '-c', '%+.6f', temp_raw_path],
        capture_output=True, text=True
      )
      exif_data = json.loads(exif_result.stdout)[0] if exif_result.stdout else {}

      date_taken = exif_data.get('DateTimeOriginal') or exif_data.get('CreateDate')
      lat = exif_data.get('GPSLatitude')
      lng = exif_data.get('GPSLongitude')
      if lat: lat = float(str(lat).replace('+', ''))
      if lng: lng = float(str(lng).replace('+', ''))

      mime_type = exif_data.get('MIMEType', '')

      if mime_type.startswith('image/'):
        filename = f"{file_id}.jpg"
        permanent_path = os.path.join(UPLOAD_FOLDER, filename)
        process_image(temp_raw_path, permanent_path)
      elif mime_type.startswith('video/'):
        filename = f"{file_id}.mp4"
        permanent_path = os.path.join(UPLOAD_FOLDER, filename)
        process_video(temp_raw_path, permanent_path)
      else:
        return jsonify({"error": f"Unsupported file type: {mime_type}"}), 400

      processed_files.append({
        "id": f"static/uploads/{filename}",
        "user_id": user_id,
        "event_id": event_id,
        "saved_filename": filename,
        "time_taken": date_taken,
        "latitude": lat,
        "longitude": lng
      })

      # Fire your database insert
      save_photo_ids_sql(user_id['id'], event_id, processed_files)

      return jsonify({
        "received": "Uploaded",
        "data": processed_files
      }), 200

    except Exception as e:
      print(f"Failed to process {original_name}: {e}")
      return jsonify({"error": str(e)}), 500

    finally:
      if os.path.exists(temp_raw_path):
        os.remove(temp_raw_path)

  # If it's not the last chunk, return status indicating successful receipt of part
  return jsonify({
    "received": "Chunk Uploaded",
    "status": f"Processing chunk {chunk_index + 1}/{total_chunks}"
  }), 200

@main.route('/api/get-footage',methods=['GET', 'POST'])
def get_photos():
  data = request.get_json()
  if not data:
    return jsonify({"status": "failed", "received": data})

  event_id = data['event_id']

  out = get_photos_from_event(event_id)
  if out:
    return jsonify({"status": "success", "received": out})
  else:
    return jsonify({"status": "failed", "received": out})
