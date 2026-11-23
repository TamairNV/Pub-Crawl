ALTER TABLE Event ADD COLUMN IF NOT EXISTS deleted_at DATETIME NULL DEFAULT NULL;
ALTER TABLE Event ADD INDEX IF NOT EXISTS idx_event_deleted_created (deleted_at, created_at);
