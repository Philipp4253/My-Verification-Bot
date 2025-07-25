"""Базовый класс для всех репозиториев."""

import aiosqlite


class BaseRepository:
    """Базовый класс репозитория."""

    def __init__(self, conn: aiosqlite.Connection):
        """
        Инициализация репозитория.

        :param conn: Соединение с базой данных.
        """
        self.conn = conn

    async def execute(self, query: str, parameters=None):
        """Выполнение SQL запроса."""
        if parameters is None:
            parameters = ()
        async with self.conn.execute(query, parameters) as cursor:
            await self.conn.commit()
            return cursor

    async def fetchone(self, query: str, parameters=None):
        """Выполнение SQL запроса и получение одной записи."""
        if parameters is None:
            parameters = ()
        async with self.conn.execute(query, parameters) as cursor:
            return await cursor.fetchone()

    async def fetchall(self, query: str, parameters=None):
        """Выполнение SQL запроса и получение всех записей."""
        if parameters is None:
            parameters = ()
        async with self.conn.execute(query, parameters) as cursor:
            return await cursor.fetchall()
