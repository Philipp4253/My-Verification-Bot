"""
Репозиторий для управления пользователями в базе данных.
"""
from typing import Optional

from .base import BaseRepository
from ..models.user import User


class UserRepository(BaseRepository):
    """
    Класс для выполнения операций CRUD над таблицей пользователей.
    """

    async def add_user(self, user: User) -> None:
        """
        Добавляет нового пользователя в базу данных.
        Если пользователь уже существует, ничего не делает.
        """
        sql = """
            INSERT OR IGNORE INTO users (telegram_id, username, first_name, last_name, language_code, is_premium)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        await self.execute(
            sql,
            (
                user.telegram_id,
                user.username,
                user.first_name,
                user.last_name,
                user.language_code,
                int(user.is_premium) if user.is_premium is not None else 0,
            ),
        )

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """
        Получает пользователя по его telegram_id.

        Возвращает объект User или None, если пользователь не найден.
        """
        sql = "SELECT * FROM users WHERE telegram_id = ?"
        row = await self.fetchone(sql, (telegram_id,))
        return User(**row) if row else None

    async def update_user_verification(
        self, telegram_id: int, verified: bool
    ) -> None:
        """
        Обновляет статус верификации пользователя.
        """
        sql = "UPDATE users SET verified = ?, verified_at = CURRENT_TIMESTAMP WHERE telegram_id = ?"
        await self.execute(sql, (int(verified), telegram_id))

    async def update_user_state(self, state: str, telegram_id: int) -> None:
        """
        Обновление состояния пользователя по его telegram_id.
        """
        sql = "UPDATE users SET state = ? WHERE telegram_id = ?"
        await self.execute(sql, (state, telegram_id))

    async def get_by_id(self, telegram_id: int) -> Optional[User]:
        """Алиас для get_user_by_telegram_id."""
        return await self.get_user_by_telegram_id(telegram_id)

    async def increment_attempts(self, telegram_id: int) -> None:
        """Увеличивает счетчик попыток верификации на 1."""
        sql = "UPDATE users SET attempts_count = attempts_count + 1 WHERE telegram_id = ?"
        await self.execute(sql, (telegram_id,))

    async def update_step(self, telegram_id: int, step: Optional[str]) -> None:
        """Обновляет текущий шаг верификации пользователя."""
        sql = "UPDATE users SET state = ? WHERE telegram_id = ?"
        await self.execute(sql, (step, telegram_id))

    async def verify_user(self, telegram_id: int) -> None:
        """Помечает пользователя как верифицированного."""
        await self.update_user_verification(telegram_id, True)

    async def get_by_username(self, username: str) -> Optional[User]:
        """
        Получает пользователя по его username.
        
        Возвращает объект User или None, если пользователь не найден.
        """
        if not username:
            return None
            
        username = username.lstrip('@')
        sql = "SELECT * FROM users WHERE username = ? COLLATE NOCASE"
        row = await self.fetchone(sql, (username,))
        return User(**row) if row else None
