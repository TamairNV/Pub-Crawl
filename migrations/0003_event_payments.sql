-- Per-event payments with Stripe Checkout (branch stripe-payments).
-- NOT run on the live DB yet. Run as MariaDB root (the app user has no DDL rights):
--   sudo mariadb pub_crawl < migrations/20261123_event_payments.sql
-- Safe to run twice (IF NOT EXISTS everywhere).

-- When an event was unlocked and which tier was bought. NULL = free event.
ALTER TABLE Event
  ADD COLUMN IF NOT EXISTS paid_at DATETIME NULL DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS paid_tier VARCHAR(16) NULL DEFAULT NULL;

-- One row per Checkout Session we create (open -> paid / expired).
CREATE TABLE IF NOT EXISTS EventPayment (
  id CHAR(36) NOT NULL DEFAULT uuid(),
  event_id CHAR(36) NOT NULL,
  stripe_session_id VARCHAR(255) NOT NULL,
  stripe_payment_intent VARCHAR(255) NULL DEFAULT NULL,
  tier VARCHAR(16) NOT NULL,
  amount_total INT NOT NULL,
  currency CHAR(3) NOT NULL DEFAULT 'gbp',
  status VARCHAR(16) NOT NULL DEFAULT 'open',
  created_by CHAR(36) NULL DEFAULT NULL,
  created_at DATETIME NOT NULL DEFAULT current_timestamp(),
  paid_at DATETIME NULL DEFAULT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_eventpayment_session (stripe_session_id),
  KEY idx_eventpayment_event (event_id, status),
  CONSTRAINT fk_eventpayment_event FOREIGN KEY (event_id) REFERENCES Event (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Stripe event ids already handled, so a retried webhook is a no-op.
CREATE TABLE IF NOT EXISTS StripeWebhookEvent (
  id VARCHAR(255) NOT NULL,
  type VARCHAR(64) NOT NULL,
  received_at DATETIME NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
