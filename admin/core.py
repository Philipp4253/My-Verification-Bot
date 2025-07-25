"""Базовые функции для административных операций."""
from aiogram.types import User
from config.settings import Settings
from bot.services.admin_service import AdminService
from loguru import logger

from bot.database.models.admin import Admin


async def user_is_admin_in_chat(
    user: User, chat_id: int, admin_service: AdminService, settings: Settings, bot=None
) -> bool:
    """
    Проверяет, является ли пользователь администратором в указанном чате,
    учитывая как глобальных, так и локальных администраторов, а также реальные права в Telegram.
    """
    if user.is_bot and user.username == "GroupAnonymousBot":
        return True

    if user.is_bot:
        return False

    if user.id in settings.admin_user_ids:
        return True

    if bot:
        try:
            chat_member = await bot.get_chat_member(chat_id, user.id)
            if chat_member.status in ["administrator", "creator"]:
                return True
        except Exception as e:
            logger.warning(f"⚠️ Не удалось проверить статус администратора для {user.id} в группе {chat_id}: {e}")

    is_admin_in_db = await admin_service.is_admin(user.id, chat_id)
    if is_admin_in_db:
        return True

    return False


async def is_group_admin(
    user: User,
    chat_id: int,
    admin_service: AdminService,
    settings: Settings
) -> bool:
    """
    Checks if a user is an administrator of a specific group.
    A user is considered an admin if they are a global admin (from .env)
    or listed as an admin for the given chat_id in the database.
    """
    if user.id in settings.admin_user_ids:
        return True

    is_admin_in_db = await admin_service.is_admin(user.id, chat_id)
    if is_admin_in_db:
        return True

    return False


async def is_admin(user_id: int, chat_id: int, admin_service: AdminService, settings: Settings) -> bool:
    """Проверяет, является ли пользователь администратором."""
    if user_id in settings.admin_user_ids:
        return True

    is_chat_admin = await admin_service.is_chat_admin(user_id, chat_id)
    if is_chat_admin:
        return True

    return False
