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
