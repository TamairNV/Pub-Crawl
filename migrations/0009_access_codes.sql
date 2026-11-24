-- Free-access codes Tamair gives to friends (app/access_codes.py). Safe to run twice.
CREATE TABLE IF NOT EXISTS AccessCode (
  id CHAR(36) NOT NULL,
  code VARCHAR(40) NOT NULL,
  label VARCHAR(120) NOT NULL DEFAULT '',
  max_uses INT NOT NULL DEFAULT 1,
  uses INT NOT NULL DEFAULT 0,
  expires_at DATETIME NULL DEFAULT NULL,
  active TINYINT(1) NOT NULL DEFAULT 1,
  created_by CHAR(36) NULL DEFAULT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_access_code (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
CREATE TABLE IF NOT EXISTS AccessCodeUse (
  id CHAR(36) NOT NULL,
  code_id CHAR(36) NOT NULL,
  event_id CHAR(36) NOT NULL,
  user_id CHAR(36) NULL DEFAULT NULL,
  used_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_code_event (code_id, event_id),
  KEY idx_code_use_event (event_id),
  CONSTRAINT fk_code_use_code FOREIGN KEY (code_id) REFERENCES AccessCode (id) ON DELETE CASCADE,
  CONSTRAINT fk_code_use_event FOREIGN KEY (event_id) REFERENCES Event (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
ALTER TABLE Event ADD COLUMN IF NOT EXISTS unlocked_by_code CHAR(36) NULL DEFAULT NULL;
