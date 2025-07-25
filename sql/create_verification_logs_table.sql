CREATE TABLE IF NOT EXISTS verification_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    method TEXT,
    full_name TEXT,
    workplace TEXT,
    website_url TEXT,
    details TEXT,
    openai_response TEXT,
    result TEXT,
    created_at TIMESTAMP
);
