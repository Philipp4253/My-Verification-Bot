-- Добавляет индекс для поиска пользователей по username
-- Исправляет ошибку: 'UserRepository' object has no attribute 'get_by_username'

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username COLLATE NOCASE);
