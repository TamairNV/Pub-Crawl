-- Per-crawl opt-out from media retention (app/maintenance.py). Safe to run twice.
ALTER TABLE Event ADD COLUMN IF NOT EXISTS keep_media TINYINT(1) NOT NULL DEFAULT 0;
