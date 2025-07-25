CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    group_id INTEGER,
    role TEXT,
    added_at TIMESTAMP,
    UNIQUE(user_id, group_id)
);
