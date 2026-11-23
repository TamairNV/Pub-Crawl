-- Organiser-owned crawls and per-crawl co-refs (app/organisers.py). Safe to run twice.
-- Existing crawls keep owner_user_id NULL, so only staff (OWNER/ADMIN) manage them, as before.
ALTER TABLE Event ADD COLUMN IF NOT EXISTS owner_user_id CHAR(36) NULL DEFAULT NULL;
ALTER TABLE Event ADD INDEX IF NOT EXISTS idx_event_owner (owner_user_id, deleted_at);
CREATE TABLE IF NOT EXISTS EventRef (
  event_id CHAR(36) NOT NULL,
  user_id CHAR(36) NOT NULL,
  added_by CHAR(36) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (event_id, user_id),
  KEY idx_event_ref_user (user_id),
  CONSTRAINT fk_event_ref_event FOREIGN KEY (event_id) REFERENCES Event (id) ON DELETE CASCADE,
  CONSTRAINT fk_event_ref_user FOREIGN KEY (user_id) REFERENCES User (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
