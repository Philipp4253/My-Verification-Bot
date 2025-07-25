"""Репозиторий для работы со счетчиком сообщений от неверифицированных пользователей."""

from typing import Optional
from .base import BaseRepository


class MessageCountRepository(BaseRepository):
    """Репозиторий для отслеживания количества сообщений от неверифицированных пользователей."""

    async def increment_count(self, user_id: int, group_id: int) -> int:
        """Увеличивает счетчик сообщений для пользователя в группе. Возвращает новое значение."""
        query = """
            INSERT INTO message_count (user_id, group_id, count, first_message_at, last_message_at)
            VALUES (?, ?, 1, datetime('now'), datetime('now'))
            ON CONFLICT(user_id, group_id) DO UPDATE SET
                count = count + 1,
                last_message_at = datetime('now')
        """
        await self.execute(query, (user_id, group_id))
        
        # Получаем текущее значение счетчика
        count_query = "SELECT count FROM message_count WHERE user_id = ? AND group_id = ?"
        row = await self.fetchone(count_query, (user_id, group_id))
        return row['count'] if row else 1

    async def get_count(self, user_id: int, group_id: int) -> int:
        """Получает текущий счетчик сообщений для пользователя в группе."""
        query = "SELECT count FROM message_count WHERE user_id = ? AND group_id = ?"
        row = await self.fetchone(query, (user_id, group_id))
        return row['count'] if row else 0

    async def reset_count(self, user_id: int, group_id: int) -> None:
        """Сбрасывает счетчик сообщений для пользователя в группе."""
        query = "DELETE FROM message_count WHERE user_id = ? AND group_id = ?"
        await self.execute(query, (user_id, group_id))

    async def cleanup_old_counts(self, days: int = 7) -> int:
        """Удаляет старые записи счетчиков (старше указанного количества дней)."""
        query = """
            DELETE FROM message_count 
            WHERE last_message_at < datetime('now', ?)
        """
        cursor = await self.execute(query, (f'-{days} days',))
        return cursor.rowcount if cursor else 0
