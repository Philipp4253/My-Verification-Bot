"""Основной класс приложения для управления ботом."""

import asyncio
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.strategy import FSMStrategy
from aiogram.fsm.storage.memory import MemoryStorage
from loguru import logger

from bot.database.manager import DatabaseManager
from bot.dispatcher_setup import setup_dispatcher
from bot.utils.commands import set_bot_commands
from config.settings import Settings

from aiogram import Bot, Dispatcher

class BotApp:
    def __init__(self):
        self.bot = Bot(token="ваш_токен")  # Лучше брать из settings
        self.dp = Dispatcher()

    async def start_polling(self):
        try:
            await self.dp.start_polling(self.bot)
        except Exception as e:
            logger.error(f"Ошибка запуска: {e}")
class BotApp:
    """
    Основной класс приложения, который инициализирует и координирует
    все компоненты бота: настройки, базу данных, диспетчер, сервисы.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.bot: Optional[Bot] = None
        self.dp: Optional[Dispatcher] = None
        self.db_manager: Optional[DatabaseManager] = None
        self._cleanup_task: Optional[asyncio.Task] = None

    async def _setup_bot_and_dispatcher(self):
        """Инициализирует бота и диспетчер."""
        self.bot = Bot(
            token=self.settings.get_telegram_bot_token(),
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        self.dp = Dispatcher(
            storage=MemoryStorage(),
            fsm_strategy=FSMStrategy.GLOBAL_USER
        )
        logger.info("Бот и диспетчер успешно настроены.")

    async def _setup_database(self):
        """Инициализирует менеджер базы данных."""
        self.db_manager = DatabaseManager(self.settings.database_path)
        await self.db_manager.init_database()
        logger.info("База данных успешно инициализирована.")

    async def _setup_dispatcher(self):
        """Настраивает и регистрирует все компоненты в диспетчере."""
        setup_dispatcher(
            dp=self.dp,
            db_manager=self.db_manager,
            settings=self.settings,
        )
        logger.info("Диспетчер полностью настроен.")

    async def _periodic_cleanup_logs(self):
        """Периодическая задача для очистки старых логов."""
        while True:
            await asyncio.sleep(24 * 60 * 60)
            try:
                deleted_count = await self.db_manager.logs.cleanup_old(
                    self.settings.auto_delete_logs_days
                )
                if deleted_count > 0:
                    logger.info(
                        f"Автоочистка: удалено {deleted_count} старых логов."
                    )
            except Exception as e:
                logger.error(f"Ошибка при автоочистке логов: {e}")

    async def on_startup(self):
        """Выполняется при старте бота."""
        logger.info("Запуск бота...")
        try:
            await set_bot_commands(self.bot)
            logger.info("Команды бота успешно установлены")
        except Exception as e:
            logger.error(f"Ошибка при установке команд бота: {e}")

        # Синхронизируем администраторов всех активных групп при запуске
        await self._sync_all_group_admins()

        self._cleanup_task = asyncio.create_task(self._periodic_cleanup_logs())
        logger.info("Периодические задачи запущены.")

    async def _sync_all_group_admins(self):
        """Синхронизирует администраторов всех активных групп при запуске бота."""
        try:
            from bot.services.admin_service import AdminService
            from bot.utils.commands import set_admin_commands_for_group
            admin_service = AdminService(self.db_manager)

            # Получаем все активные группы
            active_groups = await self.db_manager.groups.get_active()

            if not active_groups:
                logger.info("Нет активных групп для синхронизации администраторов")
                return

            logger.info(f"Синхронизация администраторов для {len(active_groups)} активных групп...")

            total_synced = 0
            for group in active_groups:
                try:
                    chat_admins = await self.bot.get_chat_administrators(group.group_id)
                    await admin_service.update_group_admins(group.group_id, chat_admins)

                    logger.debug(f"Устанавливаем команды для группы '{group.group_name}' (ID: {group.group_id})")
                    await set_admin_commands_for_group(self.bot, group.group_id)
                    logger.debug(f"Команды для группы '{group.group_name}' (ID: {group.group_id}) установлены успешно")

                    admin_count = len([admin for admin in chat_admins if not admin.user.is_bot])
                    total_synced += admin_count

                    logger.info(
                        f"✅ Группа '{group.group_name}' (ID: {group.group_id}) синхронизирована: {admin_count} админов")

                except Exception as e:
                    if "chat not found" in str(e).lower():
                        logger.info(f"⚠️ Группа '{group.group_name}' (ID: {group.group_id}) недоступна (бот не добавлен). Для возобновления работы добавьте бота в группу.")
                    else:
                        logger.warning(f"Не удалось синхронизировать администраторов для группы '{group.group_name}' ({group.group_id})")

            logger.info(
                f"Синхронизация завершена: обновлено {total_synced} администраторов в {len(active_groups)} группах")

        except Exception as e:
            logger.error(f"Ошибка при синхронизации администраторов: {e}")

    async def on_shutdown(self):
        """Выполняется при остановке бота."""
        logger.info("Остановка бота...")
        if self._cleanup_task:
            self._cleanup_task.cancel()
        if self.db_manager:
            await self.db_manager.close()
        if self.bot:
            await self.bot.session.close()
        logger.info("Все ресурсы освобождены. Бот остановлен.")

    async def run(self):
        """Главный метод для запуска бота."""
        try:
            await self._setup_bot_and_dispatcher()
            await self._setup_database()
            await self._setup_dispatcher()

            self.dp.startup.register(self.on_startup)
            self.dp.shutdown.register(self.on_shutdown)

            allowed_updates = self.dp.resolve_used_update_types()
            if "my_chat_member" not in allowed_updates:
                allowed_updates.append("my_chat_member")
            if "chat_member" not in allowed_updates:
                allowed_updates.append("chat_member")

            logger.debug(f"Типы обновлений: {allowed_updates}")

            await self.dp.start_polling(
                self.bot,
                allowed_updates=allowed_updates,
            )
        except Exception as e:
            logger.critical(f"Критическая ошибка при запуске бота: {e}", exc_info=True)
        finally:
            await self.on_shutdown()
