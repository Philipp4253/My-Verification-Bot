"""
Настройка и регистрация всех обработчиков и middleware для диспетчера.
"""
from typing import TYPE_CHECKING

from aiogram import Dispatcher
from loguru import logger

from bot.handlers.admin import admin_router
from bot.handlers.bot_lifecycle import bot_lifecycle_router
from bot.handlers.group_events import group_events_router
from bot.handlers.verification import verification_router
from bot.handlers.group_monitor import group_monitor_router
from bot.middleware.services import ServiceMiddleware
from bot.middleware.group_verification import GroupVerificationMiddleware
from config.settings import Settings


if TYPE_CHECKING:
    from bot.database.manager import DatabaseManager
    from config.settings import Settings


def setup_dispatcher(
    dp: Dispatcher,
    db_manager: "DatabaseManager",
    settings: "Settings",
) -> None:
    """
    Настраивает диспетчер, регистрируя middleware и обработчики.

    Args:
        dp: Экземпляр Dispatcher.
        db_manager: Менеджер базы данных.
        settings: Конфигурация бота.
    """
    service_middleware = ServiceMiddleware(
        db_manager=db_manager,
        settings=settings,
    )
    dp.update.middleware(service_middleware)
    
    # group_verification_middleware = GroupVerificationMiddleware(
    #     db_manager=db_manager,
    #     settings=settings,
    # )
    # dp.message.middleware(group_verification_middleware)

    dp.include_router(bot_lifecycle_router)
    dp.include_router(admin_router)
    dp.include_router(verification_router)
    
    dp.include_router(group_events_router)
    dp.include_router(group_monitor_router)

    logger.info("Все обработчики успешно зарегистрированы.")
