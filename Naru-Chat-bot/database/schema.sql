-- Run this once to set up the database:
--   mysql -u root -p --port 3307 < database/schema.sql

CREATE DATABASE IF NOT EXISTS ai_chatbot
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE ai_chatbot;

-- ── Chat history ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS chat_history (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    session_id  VARCHAR(36)   NOT NULL,
    question    TEXT          NOT NULL,
    answer      TEXT          NOT NULL,
    intent      VARCHAR(50),
    created_at  TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session (session_id),
    INDEX idx_created (created_at)
);

-- ── Learned solutions (self-learning feature) ─────────────────────────────────
CREATE TABLE IF NOT EXISTS learned_solutions (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    session_id  VARCHAR(36)   NOT NULL,
    question    TEXT          NOT NULL,
    solution    TEXT          NOT NULL,
    topic       VARCHAR(120),
    created_at  TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_ls_session (session_id),
    INDEX idx_ls_created (created_at)
);
