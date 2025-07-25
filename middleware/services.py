"""Middleware для передачи сервисов в обработчики."""

from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from loguru import logger

from bot.database.manager import DatabaseManager
from bot.services.admin_service import AdminService
from bot.services.group_service import GroupService
from bot.services.whitelist_service import WhitelistService
from bot.services.verification_service import VerificationService
from config.settings import Settings


class ServiceMiddleware(BaseMiddleware):
    """
    Middleware для передачи сервисов и менеджеров в обработчики.
    Создает сервисы "на лету" для каждого события.
    """

    def __init__(self, db_manager: DatabaseManager, settings: Settings):
        """Инициализация middleware."""
        super().__init__()
        self.db_manager = db_manager
        self.settings = settings

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Выполнение middleware."""
        
        if hasattr(event, 'from_user') and hasattr(event, 'text'):
            logger.info(f"🔧 SERVICE_MIDDLEWARE: Сообщение от {event.from_user.id if event.from_user else 'Unknown'}: '{event.text}'")

        data["db_manager"] = self.db_manager
        data["settings"] = self.settings
        data["admin_service"] = AdminService(self.db_manager)
        bot = data.get("bot")
        data["group_service"] = GroupService(self.db_manager, bot)
        data["whitelist_service"] = WhitelistService(self.db_manager)
        data["verification_service"] = VerificationService(self.db_manager)

        return await handler(event, data)
