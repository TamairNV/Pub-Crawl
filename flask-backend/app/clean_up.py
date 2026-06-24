

from SQL_manager import get_all_photos
UPLOAD_FOLDER = '../../uploads'

all_photos = get_all_photos()


import os

footage = [f for f in os.listdir(os.path.abspath(UPLOAD_FOLDER))]


all_photos = [i['id'].split('/')[-1] for i in all_photos]
counter = 0
print(all_photos)
print("----------------\n\n\n\n\n")
print(footage)
for photo in footage:
  if photo not in all_photos:
    os.remove(UPLOAD_FOLDER+f"/{photo}")
    counter +=1

print(f"{counter}: removed files")

