-- Base schema of the live pub_crawl DB as of 2026-11-23 (schema only, from mariadb-dump --no-data).
-- Safe to run twice. On the live DB this and 0001/0002 are already in place.
SET FOREIGN_KEY_CHECKS=0;
CREATE TABLE IF NOT EXISTS `Event` (
  `id` char(36) NOT NULL DEFAULT uuid(),
  `name` varchar(255) NOT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `locked` tinyint(1) DEFAULT NULL,
  `points_inversed` tinyint(1) DEFAULT NULL,
  `current_pub_id` varchar(64) DEFAULT NULL,
  `awards_voting_open` tinyint(1) NOT NULL DEFAULT 1,
  `awards_results_visible` tinyint(1) NOT NULL DEFAULT 0,
  `deleted_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_event_deleted_created` (`deleted_at`,`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
CREATE TABLE IF NOT EXISTS `EventAward` (
  `id` char(36) NOT NULL,
  `event_id` char(36) NOT NULL,
  `name` varchar(255) NOT NULL,
  `description` text DEFAULT NULL,
  `target_type` varchar(16) NOT NULL DEFAULT 'player',
  `sort_order` int(11) NOT NULL DEFAULT 0,
  `created_at` datetime DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_event_award_event` (`event_id`),
  CONSTRAINT `fk_event_award_event` FOREIGN KEY (`event_id`) REFERENCES `Event` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
CREATE TABLE IF NOT EXISTS `EventAwardVote` (
  `id` char(36) NOT NULL,
  `event_id` char(36) NOT NULL,
  `award_id` char(36) NOT NULL,
  `voter_user_id` char(36) NOT NULL,
  `nominee_id` char(36) NOT NULL,
  `nominee_type` varchar(16) NOT NULL DEFAULT 'player',
  `cast_by_user_id` char(36) DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_award_voter` (`award_id`,`voter_user_id`),
  KEY `idx_award_vote_event` (`event_id`,`award_id`),
  CONSTRAINT `fk_award_vote_award` FOREIGN KEY (`award_id`) REFERENCES `EventAward` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
CREATE TABLE IF NOT EXISTS `MiniWheel` (
  `id` char(36) NOT NULL,
  `event_id` char(36) NOT NULL,
  `name` varchar(255) NOT NULL,
  `description` text DEFAULT NULL,
  `sort_order` int(11) NOT NULL DEFAULT 0,
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_mini_wheel_event` (`event_id`),
  CONSTRAINT `fk_mini_wheel_event` FOREIGN KEY (`event_id`) REFERENCES `Event` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
CREATE TABLE IF NOT EXISTS `MiniWheelItem` (
  `id` char(36) NOT NULL,
  `wheel_id` char(36) NOT NULL,
  `label` varchar(255) NOT NULL,
  `description` text DEFAULT NULL,
  `requires_completion` tinyint(1) NOT NULL DEFAULT 1,
  `effect_type` varchar(32) NOT NULL DEFAULT 'add_points',
  `points` int(11) NOT NULL DEFAULT 1,
  `colour` varchar(32) NOT NULL DEFAULT '#fbbf24',
  `sort_order` int(11) NOT NULL DEFAULT 0,
  `created_at` datetime DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_wheel_item_wheel` (`wheel_id`),
  CONSTRAINT `fk_wheel_item_wheel` FOREIGN KEY (`wheel_id`) REFERENCES `MiniWheel` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
CREATE TABLE IF NOT EXISTS `Participant` (
  `userID` char(36) NOT NULL,
  `eventID` char(36) NOT NULL,
  `joined_at` datetime DEFAULT current_timestamp(),
  `teamID` uuid DEFAULT NULL,
  PRIMARY KEY (`userID`,`eventID`),
  KEY `fk_participant_event` (`eventID`),
  CONSTRAINT `fk_participant_event` FOREIGN KEY (`eventID`) REFERENCES `Event` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_participant_user` FOREIGN KEY (`userID`) REFERENCES `User` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
CREATE TABLE IF NOT EXISTS `Photo` (
  `id` char(255) NOT NULL,
  `user_id` char(36) NOT NULL,
  `event_id` char(36) NOT NULL,
  `time_taken` datetime DEFAULT NULL,
  `latitude` decimal(10,8) DEFAULT NULL,
  `longitude` decimal(11,8) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_photo_user` (`user_id`),
  KEY `fk_photo_event` (`event_id`),
  CONSTRAINT `fk_photo_event` FOREIGN KEY (`event_id`) REFERENCES `Event` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_photo_user` FOREIGN KEY (`user_id`) REFERENCES `User` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
CREATE TABLE IF NOT EXISTS `PlayerTask` (
  `id` char(36) NOT NULL,
  `event_id` char(36) NOT NULL,
  `user_id` char(36) NOT NULL,
  `assigned_by` char(36) DEFAULT NULL,
  `wheel_id` char(36) DEFAULT NULL,
  `wheel_item_id` char(36) DEFAULT NULL,
  `title` varchar(255) NOT NULL,
  `description` text DEFAULT NULL,
  `status` varchar(32) NOT NULL DEFAULT 'pending',
  `reward_type` varchar(32) NOT NULL DEFAULT 'add_points',
  `reward_points` int(11) NOT NULL DEFAULT 0,
  `reward_wheel_id` char(36) DEFAULT NULL,
  `spun_item_id` char(36) DEFAULT NULL,
  `spun_label` varchar(255) DEFAULT NULL,
  `spun_effect_type` varchar(32) DEFAULT NULL,
  `spun_points` int(11) DEFAULT NULL,
  `target_team_id` char(36) DEFAULT NULL,
  `player_claimed_done` tinyint(1) NOT NULL DEFAULT 0,
  `result_summary` varchar(255) DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `completed_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_player_task_event` (`event_id`,`status`),
  KEY `idx_player_task_user` (`event_id`,`user_id`,`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
CREATE TABLE IF NOT EXISTS `Point` (
  `id` char(36) NOT NULL DEFAULT uuid(),
  `eventID` char(36) NOT NULL,
  `teamID` char(36) DEFAULT NULL,
  `userID` char(36) NOT NULL,
  `refID` char(36) DEFAULT NULL,
  `point_number` int(11) NOT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `fk_point_event` (`eventID`),
  KEY `fk_point_team` (`teamID`),
  KEY `fk_point_user` (`userID`),
  CONSTRAINT `fk_point_event` FOREIGN KEY (`eventID`) REFERENCES `Event` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_point_team` FOREIGN KEY (`teamID`) REFERENCES `Team` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_point_user` FOREIGN KEY (`userID`) REFERENCES `User` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
CREATE TABLE IF NOT EXISTS `Pub` (
  `id` char(36) NOT NULL DEFAULT uuid(),
  `eventID` char(36) NOT NULL,
  `name` varchar(255) NOT NULL,
  `order_index` int(11) NOT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `fk_pub_event` (`eventID`),
  CONSTRAINT `fk_pub_event` FOREIGN KEY (`eventID`) REFERENCES `Event` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
CREATE TABLE IF NOT EXISTS `Rule` (
  `id` char(36) NOT NULL DEFAULT uuid(),
  `pubID` char(36) DEFAULT NULL,
  `name` varchar(255) NOT NULL,
  `description` text DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `event_id` char(36) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_rule_pub` (`pubID`),
  CONSTRAINT `fk_rule_pub` FOREIGN KEY (`pubID`) REFERENCES `Pub` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
CREATE TABLE IF NOT EXISTS `Team` (
  `id` char(36) NOT NULL DEFAULT uuid(),
  `name` varchar(255) DEFAULT 'bad name',
  `colour` varchar(50) DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `eventID` char(36) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_team_event` (`eventID`),
  CONSTRAINT `fk_team_event` FOREIGN KEY (`eventID`) REFERENCES `Event` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
CREATE TABLE IF NOT EXISTS `TeamPoint` (
  `id` char(36) NOT NULL,
  `event_id` char(36) NOT NULL,
  `team_id` char(36) NOT NULL,
  `ref_id` char(36) DEFAULT NULL,
  `point_number` int(11) NOT NULL,
  `reason` varchar(255) DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_team_point_event` (`event_id`,`team_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
CREATE TABLE IF NOT EXISTS `User` (
  `id` char(36) NOT NULL DEFAULT uuid(),
  `name` varchar(255) NOT NULL,
  `role` varchar(50) DEFAULT 'player',
  `teamID` char(36) DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `password` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_user_team` (`teamID`),
  CONSTRAINT `fk_user_team` FOREIGN KEY (`teamID`) REFERENCES `Team` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
SET FOREIGN_KEY_CHECKS=1;
