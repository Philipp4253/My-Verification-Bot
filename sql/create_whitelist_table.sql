CREATE TABLE IF NOT EXISTS whitelist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL,
    user_id INTEGER,
    added_by INTEGER,
    added_at TIMESTAMP,
    notes TEXT,
    username TEXT,
    input_type TEXT
);
