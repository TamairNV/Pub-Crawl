

from SQL_manager import get_all_photos
UPLOAD_FOLDER = 'static/uploads'

all_photos = get_all_photos()
print(all_photos)

import os

footage = [f for f in os.listdir(os.path.abspath(UPLOAD_FOLDER))]
print(footage)

