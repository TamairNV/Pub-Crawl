"""Maintenance jobs, run inside the backend container:

  python -m app.maintenance media            # dry run: what media retention would delete
  python -m app.maintenance media --apply    # delete it

Media retention: photos/videos of a crawl are deleted MEDIA_RETENTION_DAYS (default 90) after the crawl's
last activity (latest of Event.updated_at and its newest Point). MEDIA_RETENTION_DAYS=0 turns it off.
Crawls with Event.keep_media = 1 are never touched.
"""
import os
import sys

from .SQL_manager import _run

UPLOAD_FOLDER = '/app/static/uploads'
THUMB_FOLDER = os.path.join(UPLOAD_FOLDER, 'thumbs')


def media_due(days):
  return _run(
    "SELECT e.id, e.name, GREATEST(COALESCE(e.updated_at, e.created_at), "
    "  COALESCE((SELECT MAX(pt.created_at) FROM Point pt WHERE pt.eventID = e.id), e.created_at)) AS last_activity, "
    "  (SELECT COUNT(*) FROM Photo ph WHERE ph.event_id = e.id) AS photos "
    "FROM Event e WHERE COALESCE(e.keep_media, 0) = 0 "
    "HAVING photos > 0 AND last_activity < NOW() - INTERVAL %s DAY", [days]) or []


def delete_media(event_id):
  rows = _run("SELECT id FROM Photo WHERE event_id = %s", [event_id]) or []
  freed = 0
  for r in rows:
    base = os.path.basename(r['id'] or '')
    for path in (os.path.join(UPLOAD_FOLDER, base), os.path.join(THUMB_FOLDER, os.path.splitext(base)[0] + '.jpg')):
      if base and os.path.isfile(path):
        freed += os.path.getsize(path)
        os.remove(path)
  _run("DELETE FROM Photo WHERE event_id = %s", [event_id])
  return len(rows), freed


def main(argv):
  if len(argv) < 2 or argv[1] != 'media':
    print(__doc__)
    return 2
  days = int(os.getenv('MEDIA_RETENTION_DAYS', '90'))
  if days <= 0:
    print('media retention is off (MEDIA_RETENTION_DAYS=0)')
    return 0
  apply = '--apply' in argv
  due = media_due(days)
  if not due:
    print(f'nothing older than {days} days')
  for ev in due:
    if apply:
      n, freed = delete_media(ev['id'])
      print(f"deleted {n} media from '{ev['name']}' ({freed / 1e6:.1f} MB), last activity {ev['last_activity']}")
    else:
      print(f"would delete {ev['photos']} media from '{ev['name']}', last activity {ev['last_activity']}")
  return 0


if __name__ == '__main__':
  sys.exit(main(sys.argv))
