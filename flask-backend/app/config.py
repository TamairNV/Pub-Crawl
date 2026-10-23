import os


class Config:
  # Signs the login cookie. Must be set in .env and identical across gunicorn workers.
  SECRET_KEY = os.environ['SECRET_KEY']
  SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'true').lower() == 'true'
  SESSION_COOKIE_HTTPONLY = True
  SESSION_COOKIE_SAMESITE = 'Lax'
  PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 30
  DEBUG = True
  TESTING = True
