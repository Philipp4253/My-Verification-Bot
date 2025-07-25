"""Репозиторий для работы с таблицей admins."""

from typing import List, Optional

from ..models.admin import Admin
from .base import BaseRepository


class AdminRepository(BaseRepository):
    """Репозиторий для управления администраторами."""

    async def add(self, admin: Admin) -> None:
        """Добавление администратора."""
        query = """
            INSERT INTO admins (user_id, group_id, role, added_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(user_id, group_id) DO UPDATE SET
                role = excluded.role
        """
        await self.execute(query, (admin.user_id, admin.group_id, admin.role))

    async def remove(self, user_id: int, group_id: int) -> None:
        """Удаление администратора из группы."""
        query = "DELETE FROM admins WHERE user_id = ? AND group_id = ?"
        await self.execute(query, (user_id, group_id))

    async def get_by_group(self, group_id: int) -> List[Admin]:
        """Получение списка администраторов для конкретной группы."""
        query = "SELECT * FROM admins WHERE group_id = ?"
        rows = await self.fetchall(query, (group_id,))
        return [Admin(**row) for row in rows]

    async def exists(self, user_id: int, group_id: int) -> bool:
        """Проверка, является ли пользователь админом конкретной группы."""
        query = "SELECT 1 FROM admins WHERE user_id = ? AND group_id = ?"
        row = await self.fetchone(query, (user_id, group_id))
        return row is not None

    async def is_admin_in_any_group(self, user_id: int) -> bool:
        """Проверка, является ли пользователь админом хотя бы в одной группе."""
        query = "SELECT 1 FROM admins WHERE user_id = ? LIMIT 1"
        row = await self.fetchone(query, (user_id,))
        return row is not None

    async def remove_all_for_group(self, group_id: int) -> None:
        """Удаление всех администраторов для указанной группы."""
        query = "DELETE FROM admins WHERE group_id = ?"
        await self.execute(query, (group_id,))

    async def get_user_groups(self, user_id: int) -> List[int]:
        """Получение списка ID групп, где пользователь является админом."""
        query = "SELECT group_id FROM admins WHERE user_id = ?"
        rows = await self.fetchall(query, (user_id,))
        return [row['group_id'] for row in rows]
