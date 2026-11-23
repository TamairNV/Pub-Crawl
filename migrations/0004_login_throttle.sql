-- Failed-login counter for rate limiting (app/security.py). Safe to run twice.
CREATE TABLE IF NOT EXISTS LoginAttempt (
  id BIGINT NOT NULL AUTO_INCREMENT,
  ip VARCHAR(64) NOT NULL,
  name VARCHAR(255) NOT NULL,
  success TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_login_name (name, created_at),
  KEY idx_login_ip (ip, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
