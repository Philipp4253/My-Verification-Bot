CREATE TABLE IF NOT EXISTS message_count (
    user_id INTEGER NOT NULL,
    group_id INTEGER NOT NULL,
    count INTEGER DEFAULT 1,
    first_message_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_message_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, group_id)
);
