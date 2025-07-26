"""Сервис для управления администраторами."""

from typing import List
from aiogram.types import ChatMember
from loguru import logger

from bot.database.manager import DatabaseManager
from bot.database.models.admin import Admin
from bot.database.models.group import Group


class AdminService:
    """Сервис для бизнес-логики, связанной с администраторами."""

    def __init__(self, db_manager: DatabaseManager):
        """
        Инициализация сервиса.

        :param db_manager: Менеджер базы данных.
        """
        self.db = db_manager

    async def update_group_admins(self, group_id: int, chat_admins: List[ChatMember]) -> None:
        """
        Обновляет список администраторов для группы.

        - Удаляет старых администраторов.
        - Добавляет новых администраторов.

        :param group_id: ID группы.
        :param chat_admins: Список администраторов из Telegram API.
        """
        await self.db.admins.remove_all_for_group(group_id)

        for admin_member in chat_admins:
            if not admin_member.user.is_bot or admin_member.user.id == 1087968824:
                admin = Admin(
                    user_id=admin_member.user.id,
                    group_id=group_id,
                    role=admin_member.status
                )
                await self.db.admins.add(admin)


    async def is_admin(self, user_id: int, group_id: int) -> bool:
        """
        Проверяет, является ли пользователь администратором группы по данным из БД.

        :param user_id: ID пользователя.
        :param group_id: ID группы.
        :return: True, если пользователь является администратором.
        """
        return await self.db.admins.exists(user_id, group_id)

    async def is_user_admin_in_any_group(self, user_id: int) -> bool:
        """
        Проверяет, является ли пользователь администратором хотя бы в одной группе.

        :param user_id: ID пользователя.
        :return: True, если пользователь является администратором хотя бы в одной группе.
        """
        try:
            admins = await self.db.admins.get_user_groups(user_id)
            return len(admins) > 0
        except Exception as e:
            logger.error(f"Ошибка при проверке администратора {user_id}: {e}")
            return False

    async def get_group_info(self, group_id: int) -> Group | None:
        """
        Возвращает информацию о группе по ее ID.

        :param group_id: ID группы.
        :return: Объект группы или None, если группа не найдена.
        """
        return await self.db.groups.get_by_id(group_id)

async def is_user_verified(self, user_id: int, chat_id: int) -> bool:
    """Проверяет, прошел ли пользователь верификацию в указанном чате"""
    # Реализуй этот метод в соответствии с твоей структурой базы данных
    # Должен возвращать True, если пользователь верифицирован
async def check_unverified_users(self, chat_id: int, hours_limit: int = 24):
    """Проверяет и удаляет неверифицированных пользователей"""
    try:
        # Получаем неверифицированных пользователей
        unverified = await self.get_unverified_users(chat_id)
        
        # Фильтруем тех, кто давно в группе
        now = datetime.now()
        to_remove = []
        
        for user_id, join_date in unverified:
            if (now - join_date).total_seconds() > hours_limit * 3600:
                to_remove.append(user_id)
        
        # Удаляем пользователей
        for user_id in to_remove:
            try:
                await self.bot.ban_chat_member(chat_id, user_id)
                await self.bot.unban_chat_member(chat_id, user_id)  # Разбаниваем, чтобы могли вернуться
                logger.info(f"Удален неверифицированный пользователь {user_id} из чата {chat_id}")
            except Exception as e:
                logger.error(f"Ошибка при удалении {user_id}: {e}")
        
        return len(to_remove)
    except Exception as e:
        logger.error(f"Ошибка в check_unverified_users: {e}")
        return 0
async def get_verified_users(self, chat_id: int) -> list[tuple[int, str]]:
    """Возвращает список верифицированных пользователей (user_id, username)"""
    # Реализация зависит от твоей БД

async def get_unverified_users(self, chat_id: int) -> list[tuple[int, str, datetime]]:
    """Возвращает список неверифицированных пользователей с датой вступления"""
    # Реализация зависит от твоей БД
