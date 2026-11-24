-- Per-crawl feature switches (app/setup_wizard.py) and indexes for the hot polling queries. Safe to run twice.
ALTER TABLE Event ADD COLUMN IF NOT EXISTS features TEXT NULL DEFAULT NULL;
ALTER TABLE Point ADD INDEX IF NOT EXISTS idx_point_event_user (eventID, userID);
ALTER TABLE Participant ADD INDEX IF NOT EXISTS idx_participant_event_team (eventID, teamID);
ALTER TABLE Pub ADD INDEX IF NOT EXISTS idx_pub_event_order (eventID, order_index);
ALTER TABLE Rule ADD INDEX IF NOT EXISTS idx_rule_event_pub (event_id, pubID);
ALTER TABLE Photo ADD INDEX IF NOT EXISTS idx_photo_event_time (event_id, time_taken);
