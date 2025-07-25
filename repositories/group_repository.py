"""Репозиторий для работы с таблицей groups."""

from datetime import datetime
from typing import Optional

import aiosqlite
from .base import BaseRepository
from ..models.group import Group


class GroupRepository(BaseRepository):
    """Репозиторий для управления группами."""

    def __init__(self, conn: aiosqlite.Connection):
        """Инициализация репозитория."""
        super().__init__(conn)

    async def add_or_update(self, group: Group) -> None:
        """Добавление или обновление информации о группе."""
        now = datetime.now()
        added_at = group.added_at or now
        updated_at = now

        query = """
            INSERT INTO groups (group_id, group_name, is_active, added_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(group_id) DO UPDATE SET
                group_name = excluded.group_name,
                is_active = excluded.is_active,
                added_at = COALESCE(groups.added_at, excluded.added_at),
                updated_at = excluded.updated_at
        """
        async with self.conn.cursor() as cursor:
            await cursor.execute(query, (
                group.group_id, group.group_name, int(group.is_active),
                added_at, updated_at
            ))
            await self.conn.commit()

    async def get_by_id(self, group_id: int) -> Optional[Group]:
        """Получение информации о группе по ID."""
        query = "SELECT * FROM groups WHERE group_id = ?"
        async with self.conn.cursor() as cursor:
            await cursor.execute(query, (group_id,))
            row = await cursor.fetchone()
            return Group(**dict(row)) if row else None

    async def get_active(self) -> list[Group]:
        """Получение списка всех активных групп."""
        query = "SELECT * FROM groups WHERE is_active = 1"
        async with self.conn.cursor() as cursor:
            await cursor.execute(query)
            rows = await cursor.fetchall()
            return [Group(**dict(row)) for row in rows]

    async def set_active_status(self, group_id: int, is_active: bool) -> None:
        """Установка статуса активности для группы."""
        query = "UPDATE groups SET is_active = ?, updated_at = ? WHERE group_id = ?"
        now = datetime.now()
        async with self.conn.cursor() as cursor:
            await cursor.execute(query, (int(is_active), now, group_id))
            await self.conn.commit()

    async def toggle_checkin_mode(self, group_id: int) -> bool:
        """Переключение режима checkin для группы. Возвращает новое значение."""
        query = """
            UPDATE groups 
            SET checkin_mode = NOT checkin_mode, updated_at = ? 
            WHERE group_id = ?
        """
        now = datetime.now()
        async with self.conn.cursor() as cursor:
            await cursor.execute(query, (now, group_id))
            await self.conn.commit()
            
        group = await self.get_by_id(group_id)
        return group.checkin_mode if group else False

    async def is_checkin_mode_enabled(self, group_id: int) -> bool:
        """Проверка, включен ли режим checkin для группы."""
        query = "SELECT checkin_mode FROM groups WHERE group_id = ?"
        async with self.conn.cursor() as cursor:
            await cursor.execute(query, (group_id,))
            row = await cursor.fetchone()
            return bool(row['checkin_mode']) if row else False
