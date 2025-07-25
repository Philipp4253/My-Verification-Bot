"""Репозиторий для работы с таблицей verification_logs."""

from .base import BaseRepository
from ..models.verification_log import VerificationLog


class LogRepository(BaseRepository):
    """Репозиторий для управления логами верификации."""

    async def add(self, log: VerificationLog) -> None:
        """Добавление лога верификации в базу данных."""
        query = """
            INSERT INTO verification_logs (user_id, method, full_name, workplace, website_url, details, openai_response, result, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """
        await self.execute(
            query,
            (
                log.user_id,
                log.method.value if log.method else None,
                log.full_name,
                log.workplace,
                log.website_url,
                log.details,
                log.openai_response,
                log.result,
            ),
        )

    async def cleanup_old(self, days: int) -> int:
        """Удаление старых логов верификации."""
        query = "DELETE FROM verification_logs WHERE created_at < datetime('now', ?)"
        params = (f'-{days} days',)
        cursor = await self.execute(query, params)
        return cursor.rowcount if cursor else 0

    async def update_verification_result(self, user_id: int, result: str) -> None:
        """Обновление результата верификации для последнего лога пользователя."""
        query = """
            UPDATE verification_logs 
            SET result = ? 
            WHERE user_id = ? AND id = (
                SELECT id FROM verification_logs 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
            )
        """
        await self.execute(query, (result, user_id, user_id))
