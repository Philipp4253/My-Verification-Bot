"""Основной класс приложения для управления ботом."""
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

class BotApp:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.bot: Bot = None
        self.dp: Dispatcher = None
        self.db_manager: DatabaseManager = None

    async def start_polling(self):
        """Альтернативное имя для метода run (для совместимости)"""
        await self.run()

    async def run(self):
        """Основной метод запуска бота."""
        try:
            await self._setup_components()
            await self.dp.start_polling(self.bot)
        except Exception as e:
            logger.critical(f"Ошибка запуска: {e}")
        finally:
            await self._shutdown()

    async def _setup_components(self):
        """Инициализирует все компоненты бота."""
        self.bot = Bot(
            token=self.settings.get_telegram_bot_token(),
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        self.dp = Dispatcher(storage=MemoryStorage(), fsm_strategy=FSMStrategy.GLOBAL_USER)
        self.db_manager = DatabaseManager(self.settings.database_path)
        
        await self.db_manager.init_database()
        setup_dispatcher(self.dp, self.db_manager, self.settings)
        await set_bot_commands(self.bot)

    async def _shutdown(self):
        """Корректное завершение работы."""
        if hasattr(self, 'db_manager') and self.db_manager:
            await self.db_manager.close()
        if hasattr(self, 'bot') and self.bot:
            await self.bot.session.close()
async def start_polling(self):
    """Алиас для run() для совместимости"""
    await self.run()
