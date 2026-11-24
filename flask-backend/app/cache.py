"""Tiny per-worker TTL cache for hot, shared reads (leaderboard, current pub, wheels...).

Phones poll every few seconds; a burst of 200 players would otherwise hit MariaDB with the same
queries hundreds of times a second. Entries live a few seconds, so scores are at most that stale for
players. Refs/organisers bypass the cache, so their own taps always show straight away.
"""
import threading
import time

_store = {}
_lock = threading.Lock()
MAX_ENTRIES = 5000


def cached(key, ttl, fn):
  now = time.monotonic()
  with _lock:
    hit = _store.get(key)
    if hit and hit[0] > now:
      return hit[1]
  value = fn()
  if value is not False and value is not None:
    with _lock:
      if len(_store) > MAX_ENTRIES:
        for k in [k for k, v in _store.items() if v[0] <= now]:
          _store.pop(k, None)
        if len(_store) > MAX_ENTRIES:
          _store.clear()
      _store[key] = (now + ttl, value)
  return value


def forget(prefix):
  with _lock:
    for k in [k for k in _store if k[0] == prefix]:
      _store.pop(k, None)
