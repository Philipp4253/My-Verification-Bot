from pathlib import Path
from typing import Optional
import os

from loguru import logger
import aiosqlite

from bot.database.repositories.user_repository import UserRepository
from bot.database.repositories.group_repository import GroupRepository
from bot.database.repositories.admin_repository import AdminRepository
from bot.database.repositories.whitelist_repository import WhitelistRepository
from bot.database.repositories.log_repository import LogRepository
from bot.database.repositories.user_group_verification_repository import UserGroupVerificationRepository
from bot.database.repositories.message_count_repository import MessageCountRepository


class DatabaseManager:
    """
    Управление базой данных SQLite и репозиториями.

    Отвечает за инициализацию соединения и создание таблиц,
    а также предоставляет доступ к репозиториям для работы с данными.
    """

    def __init__(self, db_path: str):
        """Инициализация менеджера базы данных."""
        self.db_path = db_path
        self.conn: Optional[aiosqlite.Connection] = None
        self.users: Optional[UserRepository] = None
        self.groups: Optional[GroupRepository] = None
        self.admins: Optional[AdminRepository] = None
        self.whitelist: Optional[WhitelistRepository] = None
        self.logs: Optional[LogRepository] = None
        self.user_group_verifications: Optional[UserGroupVerificationRepository] = None
        self.message_counts: Optional[MessageCountRepository] = None

    async def init_database(self) -> None:
        """Инициализация соединения с базой данных и создание таблиц."""
        self.conn = await aiosqlite.connect(self.db_path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA foreign_keys = ON;")
        await self._run_sql_scripts()

        # Миграция: добавляем поле requires_verification если его нет
        await self._migrate_add_requires_verification_field()
        await self._migrate_add_checkin_mode_field()
        await self._migrate_add_username_index()

        await self._init_repositories()
        logger.info("База данных и репозитории успешно инициализированы")

    async def _init_repositories(self) -> None:
        """Инициализация всех репозиториев."""
        self.users = UserRepository(self.conn)
        self.groups = GroupRepository(self.conn)
        self.admins = AdminRepository(self.conn)
        self.whitelist = WhitelistRepository(self.conn)
        self.logs = LogRepository(self.conn)
        self.user_group_verifications = UserGroupVerificationRepository(self.conn)
        self.message_counts = MessageCountRepository(self.conn)

    async def _run_sql_scripts(self) -> None:
        """
        Выполнение SQL-скриптов для создания таблиц.

        Скрипты читаются из директории bot/database/sql
        и выполняются в алфавитном порядке.
        """
        sql_dir = Path(__file__).parent / "sql"
        scripts = sorted(sql_dir.glob("*.sql"))

        async with self.conn.cursor() as cursor:
            for script_path in scripts:
                try:
                    with open(script_path, "r", encoding="utf-8") as f:
                        sql_query = f.read().strip()
                        await cursor.execute(sql_query)
                except Exception as e:
                    logger.error(f"❌ Ошибка выполнения SQL-скрипта {script_path.name}: {e}")
                    raise

        await self.conn.commit()
        logger.info(f"Инициализация БД завершена: выполнено {len(scripts)} SQL-скриптов")

    async def close(self) -> None:
        """Закрытие соединения с базой данных."""
        if self.conn:
            await self.conn.close()
            logger.info("Соединение с базой данных закрыто")

    async def initialize(self):
        """Инициализирует базу данных и создает все необходимые таблицы."""
        sql_files = [
            "create_users_table.sql",
            "create_groups_table.sql",
            "create_admins_table.sql",
            "create_verification_logs_table.sql",
            "create_whitelist_table.sql",
            "z_create_user_group_verifications_table.sql",
            "z_create_whitelist_index.sql"
        ]

        for sql_file in sql_files:
            file_path = os.path.join(os.path.dirname(__file__), "sql", sql_file)
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    sql = f.read()
                await self.execute(sql)
                logger.info(f"Выполнен SQL файл: {sql_file}")
            else:
                logger.warning(f"SQL файл не найден: {sql_file}")

        # Миграция: добавляем поле requires_verification если его нет
        await self._migrate_add_requires_verification_field()

        logger.info("База данных инициализирована")

    async def _migrate_add_requires_verification_field(self):
        """Миграция: добавляет поля requires_verification и verification_type если их нет."""
        try:
            # Проверяем, существуют ли уже поля
            cursor = await self.conn.execute("PRAGMA table_info(user_group_verifications)")
            columns = await cursor.fetchall()
            column_names = [column[1] for column in columns]

            # Добавляем requires_verification если его нет
            if 'requires_verification' not in column_names:
                await self.conn.execute(
                    "ALTER TABLE user_group_verifications ADD COLUMN requires_verification BOOLEAN DEFAULT FALSE"
                )
                await self.conn.commit()
                logger.info("Добавлено поле requires_verification в таблицу user_group_verifications")
            else:
                logger.debug("Поле requires_verification уже существует")

            # Добавляем verification_type если его нет
            if 'verification_type' not in column_names:
                await self.conn.execute(
                    "ALTER TABLE user_group_verifications ADD COLUMN verification_type TEXT"
                )
                await self.conn.commit()
                logger.info("Добавлено поле verification_type в таблицу user_group_verifications")
            else:
                logger.debug("Поле verification_type уже существует")

        except Exception as e:
            logger.error(f"Ошибка при миграции полей user_group_verifications: {e}")
            raise

    async def _migrate_add_checkin_mode_field(self):
        """Миграция: добавляет поле checkin_mode в таблицу groups если его нет."""
        try:
            cursor = await self.conn.execute("PRAGMA table_info(groups)")
            columns = await cursor.fetchall()
            column_names = [column[1] for column in columns]

            if 'checkin_mode' not in column_names:
                await self.conn.execute(
                    "ALTER TABLE groups ADD COLUMN checkin_mode BOOLEAN DEFAULT FALSE"
                )
                await self.conn.commit()
                logger.info("Добавлено поле checkin_mode в таблицу groups")
            else:
                logger.debug("Поле checkin_mode уже существует")

        except Exception as e:
            logger.error(f"Ошибка при миграции поля checkin_mode: {e}")
            raise

    async def _migrate_add_username_index(self):
        """Миграция: добавляет индекс для поиска пользователей по username."""
        try:
            await self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username COLLATE NOCASE)"
            )
            await self.conn.commit()
            logger.info("Добавлен индекс idx_users_username для таблицы users")
        except Exception as e:
            logger.error(f"Ошибка при добавлении индекса username: {e}")
            raise

    async def execute(self, query: str, params=None):
        """Выполняет SQL запрос."""
        async with self.conn.cursor() as cursor:
            if params:
                await cursor.execute(query, params)
            else:
                await cursor.execute(query)
            await self.conn.commit()
