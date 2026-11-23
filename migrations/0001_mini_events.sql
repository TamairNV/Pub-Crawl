CREATE TABLE IF NOT EXISTS MiniWheel (
  id CHAR(36) PRIMARY KEY,
  event_id CHAR(36) NOT NULL,
  name VARCHAR(255) NOT NULL,
  description TEXT NULL,
  sort_order INT NOT NULL DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_mini_wheel_event (event_id),
  CONSTRAINT fk_mini_wheel_event FOREIGN KEY (event_id) REFERENCES Event(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS MiniWheelItem (
  id CHAR(36) PRIMARY KEY,
  wheel_id CHAR(36) NOT NULL,
  label VARCHAR(255) NOT NULL,
  description TEXT NULL,
  requires_completion TINYINT(1) NOT NULL DEFAULT 1,
  effect_type VARCHAR(32) NOT NULL DEFAULT 'add_points',
  points INT NOT NULL DEFAULT 1,
  colour VARCHAR(32) NOT NULL DEFAULT '#fbbf24',
  sort_order INT NOT NULL DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_wheel_item_wheel (wheel_id),
  CONSTRAINT fk_wheel_item_wheel FOREIGN KEY (wheel_id) REFERENCES MiniWheel(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS PlayerTask (
  id CHAR(36) PRIMARY KEY,
  event_id CHAR(36) NOT NULL,
  user_id CHAR(36) NOT NULL,
  assigned_by CHAR(36) NULL,
  wheel_id CHAR(36) NULL,
  wheel_item_id CHAR(36) NULL,
  title VARCHAR(255) NOT NULL,
  description TEXT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  reward_type VARCHAR(32) NOT NULL DEFAULT 'add_points',
  reward_points INT NOT NULL DEFAULT 0,
  reward_wheel_id CHAR(36) NULL,
  spun_item_id CHAR(36) NULL,
  spun_label VARCHAR(255) NULL,
  spun_effect_type VARCHAR(32) NULL,
  spun_points INT NULL,
  target_team_id CHAR(36) NULL,
  player_claimed_done TINYINT(1) NOT NULL DEFAULT 0,
  result_summary VARCHAR(255) NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  completed_at DATETIME NULL,
  INDEX idx_player_task_event (event_id, status),
  INDEX idx_player_task_user (event_id, user_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS TeamPoint (
  id CHAR(36) PRIMARY KEY,
  event_id CHAR(36) NOT NULL,
  team_id CHAR(36) NOT NULL,
  ref_id CHAR(36) NULL,
  point_number INT NOT NULL,
  reason VARCHAR(255) NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_team_point_event (event_id, team_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS EventAward (
  id CHAR(36) PRIMARY KEY,
  event_id CHAR(36) NOT NULL,
  name VARCHAR(255) NOT NULL,
  description TEXT NULL,
  target_type VARCHAR(16) NOT NULL DEFAULT 'player',
  sort_order INT NOT NULL DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_event_award_event (event_id),
  CONSTRAINT fk_event_award_event FOREIGN KEY (event_id) REFERENCES Event(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS EventAwardVote (
  id CHAR(36) PRIMARY KEY,
  event_id CHAR(36) NOT NULL,
  award_id CHAR(36) NOT NULL,
  voter_user_id CHAR(36) NOT NULL,
  nominee_id CHAR(36) NOT NULL,
  nominee_type VARCHAR(16) NOT NULL DEFAULT 'player',
  cast_by_user_id CHAR(36) NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_award_voter (award_id, voter_user_id),
  INDEX idx_award_vote_event (event_id, award_id),
  CONSTRAINT fk_award_vote_award FOREIGN KEY (award_id) REFERENCES EventAward(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

ALTER TABLE Event ADD COLUMN IF NOT EXISTS awards_voting_open TINYINT(1) NOT NULL DEFAULT 1;
ALTER TABLE Event ADD COLUMN IF NOT EXISTS awards_results_visible TINYINT(1) NOT NULL DEFAULT 0;
