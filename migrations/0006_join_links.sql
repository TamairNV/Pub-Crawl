-- QR / link join with guest players (app/join.py). Safe to run twice.
ALTER TABLE Event ADD COLUMN IF NOT EXISTS join_token VARCHAR(64) NULL DEFAULT NULL;
ALTER TABLE Event ADD COLUMN IF NOT EXISTS max_players INT NULL DEFAULT NULL;
ALTER TABLE Event ADD UNIQUE INDEX IF NOT EXISTS uq_event_join_token (join_token);
ALTER TABLE User ADD INDEX IF NOT EXISTS idx_user_name (name);
