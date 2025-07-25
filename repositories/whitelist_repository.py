"""Репозиторий для работы с белым списком."""

from typing import Optional, List
from .base import BaseRepository
from ..models.whitelist_entry import WhitelistEntry


class WhitelistRepository(BaseRepository):
    """Репозиторий для управления белым списком пользователей."""

    async def add_by_user_id(self, user_id: int, group_id: int, username: Optional[str] = None, full_name: Optional[str] = None) -> None:
        """Добавляет пользователя в белый список по user_id."""
        existing = await self.get_by_user_id(user_id, group_id)
        if existing:
            await self.connection.execute(
                """UPDATE whitelist SET username = $1, full_name = $2, updated_at = NOW()
                   WHERE user_id = $3 AND group_id = $4""",
                username, full_name, user_id, group_id
            )
        else:
            await self.connection.execute(
                """INSERT INTO whitelist (user_id, group_id, username, full_name, created_at, updated_at)
                   VALUES ($1, $2, $3, $4, NOW(), NOW())""",
                user_id, group_id, username, full_name
            )

    async def add_by_username(self, username: str, group_id: int) -> None:
        """Добавляет пользователя в белый список по username."""
        existing = await self.get_by_username(username, group_id)
        if existing:
            return

        await self.connection.execute(
            """INSERT INTO whitelist (username, group_id, created_at, updated_at)
               VALUES ($1, $2, NOW(), NOW())""",
            username, group_id
        )

    async def remove_by_user_id(self, user_id: int, group_id: int) -> bool:
        """Удаляет пользователя из белого списка по user_id."""
        result = await self.connection.execute(
            "DELETE FROM whitelist WHERE user_id = $1 AND group_id = $2",
            user_id, group_id
        )
        return result != "DELETE 0"

    async def add(self, entry: WhitelistEntry) -> None:
        """Добавление пользователя в whitelist."""
        if entry.user_id:
            existing_query = "SELECT 1 FROM whitelist WHERE user_id = ? AND group_id = ?"
            existing = await self.fetchone(existing_query, (entry.user_id, entry.group_id))

            if existing:
                update_query = """
                    UPDATE whitelist
                    SET added_by = ?, notes = ?, username = ?, input_type = ?, added_at = datetime('now')
                    WHERE user_id = ? AND group_id = ?
                """
                await self.execute(
                    update_query,
                    (
                        entry.added_by,
                        entry.notes,
                        entry.username,
                        entry.input_type,
                        entry.user_id,
                        entry.group_id,
                    ),
                )
            else:
                insert_query = """
                    INSERT INTO whitelist (group_id, user_id, added_by, added_at, notes, username, input_type)
                    VALUES (?, ?, ?, datetime('now'), ?, ?, ?)
                """
                await self.execute(
                    insert_query,
                    (
                        entry.group_id,
                        entry.user_id,
                        entry.added_by,
                        entry.notes,
                        entry.username,
                        entry.input_type,
                    ),
                )
        elif entry.username:
            existing_query = "SELECT 1 FROM whitelist WHERE username = ? AND group_id = ?"
            existing = await self.fetchone(existing_query, (entry.username, entry.group_id))

            if not existing:
                insert_query = """
                    INSERT INTO whitelist (group_id, user_id, added_by, added_at, notes, username, input_type)
                    VALUES (?, NULL, ?, datetime('now'), ?, ?, 'username')
                """
                await self.execute(
                    insert_query,
                    (
                        entry.group_id,
                        entry.added_by,
                        entry.notes,
                        entry.username,
                    ),
                )
        else:
            raise ValueError("Необходимо указать user_id или username")

    async def remove(self, user_id: int, group_id: int) -> bool:
        """Удаление пользователя из whitelist."""
        query = "DELETE FROM whitelist WHERE user_id = ? AND group_id = ?"
        cursor = await self.execute(query, (user_id, group_id))
        return cursor.rowcount > 0

    async def is_whitelisted(self, user_id: int, group_id: int) -> bool:
        """Проверка, находится ли пользователь в whitelist."""
        query = "SELECT 1 FROM whitelist WHERE user_id = ? AND group_id = ?"
        row = await self.fetchone(query, (user_id, group_id))
        return row is not None

    async def get(self, group_id: int, user_id: int) -> WhitelistEntry:
        """Получение записи whitelist по group_id и user_id."""
        query = "SELECT * FROM whitelist WHERE group_id = ? AND user_id = ?"
        row = await self.fetchone(query, (group_id, user_id))
        return WhitelistEntry(**row) if row else None

    async def get_by_group(self, group_id: int) -> List[WhitelistEntry]:
        """Получение списка whitelist для группы."""
        query = "SELECT * FROM whitelist WHERE group_id = ?"
        rows = await self.fetchall(query, (group_id,))
        return [WhitelistEntry(**row) for row in rows]

    async def remove_by_id(self, entry_id: int) -> None:
        """Удаление записи whitelist по ID записи."""
        query = "DELETE FROM whitelist WHERE id = ?"
        await self.execute(query, (entry_id,))

    async def get_all(self) -> List[WhitelistEntry]:
        """Получение всех записей whitelist."""
        query = "SELECT * FROM whitelist"
        rows = await self.fetchall(query)
        return [WhitelistEntry(**row) for row in rows]
