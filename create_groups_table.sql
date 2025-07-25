CREATE TABLE IF NOT EXISTS groups (
    group_id INTEGER PRIMARY KEY,
    group_name TEXT,
    is_active BOOLEAN,
    added_at TIMESTAMP,
    updated_at TIMESTAMP
);
