-- Offline ref taps carry a client UUID so a retried request only scores once. Safe to run twice.
ALTER TABLE Point ADD COLUMN IF NOT EXISTS client_id CHAR(36) NULL DEFAULT NULL;
ALTER TABLE Point ADD UNIQUE INDEX IF NOT EXISTS uq_point_client_id (client_id);
