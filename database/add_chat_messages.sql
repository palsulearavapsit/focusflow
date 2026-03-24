-- ================================================================
-- FocusFlow - Discussion Forum: chat_messages table
-- Run this SQL in your MySQL database to enable the chat feature.
-- ================================================================

CREATE TABLE IF NOT EXISTS chat_messages (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    sender_id    INT NOT NULL,
    receiver_id  INT NOT NULL,
    content      TEXT NOT NULL,
    is_read      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Foreign key constraints ensure only valid users can send/receive
    FOREIGN KEY (sender_id)   REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE,

    -- Index for fast privacy-enforced queries
    INDEX idx_conversation (sender_id, receiver_id),
    INDEX idx_receiver_unread (receiver_id, is_read)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
