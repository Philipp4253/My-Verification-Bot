import logging
from typing import List

from bot.database.manager import DatabaseManager
from bot.database.models.whitelist_entry import WhitelistEntry
from bot.database.repositories.whitelist_repository import WhitelistRepository

logger = logging.getLogger(__name__)


class WhitelistService:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.whitelist_repo: WhitelistRepository = self.db_manager.whitelist

    async def add_to_whitelist(self, group_id: int, user_id: int = None, added_by_admin_id: int = None, username: str = None) -> bool:
        """Добавляет пользователя в белый список группы по ID или username."""
        entry = WhitelistEntry(
            group_id=group_id,
            user_id=user_id,
            username=username,
            added_by=added_by_admin_id,
        )
        try:
            await self.whitelist_repo.add(entry)
            identifier = f"@{username}" if username else str(user_id)
            logger.info(
                f"Пользователь {identifier} добавлен в белый список группы {group_id} администратором {added_by_admin_id}.")
            
            await self._auto_complete_verification(user_id, group_id, username)
            
            return True
        except Exception as e:
            identifier = f"@{username}" if username else str(user_id)
            logger.error(f"Ошибка добавления пользователя {identifier} в белый список группы {group_id}: {e}")
            return False

    async def remove_from_whitelist(self, group_id: int, user_id: int) -> bool:
        """Удаляет пользователя из белого списка группы."""
        try:
            success = await self.whitelist_repo.remove(user_id, group_id)
            if success:
                logger.info(f"Пользователь {user_id} удален из белого списка группы {group_id}.")
            else:
                logger.warning(
                    f"Попытка удалить несуществующего пользователя {user_id} из белого списка группы {group_id}.")
            return success
        except Exception as e:
            logger.error(f"Ошибка удаления пользователя {user_id} из белого списка группы {group_id}: {e}")
            return False

    async def is_whitelisted(self, group_id: int, user_id: int) -> bool:
        """Проверяет, находится ли пользователь в белом списке группы."""
        entry = await self.whitelist_repo.get(group_id, user_id)
        return entry is not None

    async def is_in_whitelist(self, user_id: int, username: str = None, group_id: int = None) -> bool:
        """Проверяет по ID и username, есть ли пользователь в whitelist."""
        if not group_id:
            return False

        if await self.whitelist_repo.is_whitelisted(user_id, group_id):
            return True

        if username:
            entries = await self.whitelist_repo.get_by_group(group_id)
            for entry in entries:
                if entry.username == username:
                    return True

        return False

    async def get_whitelist(self, group_id: int) -> List[WhitelistEntry]:
        """Возвращает всех пользователей в белом списке для указанной группы."""
        return await self.whitelist_repo.get_by_group(group_id)

    async def remove_by_entry_id(self, entry_id: int) -> bool:
        """Удаляет запись из whitelist по ID записи."""
        try:
            await self.whitelist_repo.remove_by_id(entry_id)
            logger.info(f"Запись whitelist с ID {entry_id} удалена.")
            return True
        except Exception as e:
            logger.error(f"Ошибка удаления записи whitelist с ID {entry_id}: {e}")
            return False

    async def check_user_in_whitelist(self, user_id: int, username: str = None, group_id: int = None) -> bool:
        """Проверяет, находится ли пользователь в whitelist для указанной группы."""
        if not group_id:
            entries = await self.whitelist_repo.get_all()
            for entry in entries:
                if entry.user_id == user_id or (username and entry.username == username):
                    return True
            return False

        return await self.is_in_whitelist(user_id, username, group_id)

    async def auto_verify_whitelist_user(self, user_id: int, username: str = None, group_id: int = None) -> bool:
        """Автоматически верифицирует пользователя из whitelist для конкретной группы."""
        try:
            if not group_id:
                logger.error("Не указан group_id для автоматической верификации")
                return False

            user = await self.db_manager.users.get_by_id(user_id)
            if not user:
                from bot.database.models.user import User
                user = User(
                    telegram_id=user_id,
                    username=username,
                    first_name="Unknown",
                    last_name="",
                    language_code="ru",
                    is_premium=False
                )
                await self.db_manager.users.add_user(user)

            verification = await self.db_manager.user_group_verifications.get_by_user_and_group(user_id, group_id)
            if not verification:
                verification = await self.db_manager.user_group_verifications.get_or_create(user_id, group_id)

            if not verification.verified:
                await self.db_manager.user_group_verifications.update_verified_status(user_id, group_id, True, "whitelist")
                await self.db_manager.user_group_verifications.update_requires_verification(user_id, group_id, False)
                logger.info(
                    f"Пользователь {user_id} ({username}) автоматически верифицирован через whitelist в группе {group_id}")
                return True

            return True
        except Exception as e:
            logger.error(f"Ошибка автоматической верификации пользователя {user_id} в группе {group_id}: {e}")
            return False

    async def _auto_complete_verification(self, user_id: int, group_id: int, username: str = None):
        """Автоматически завершает любую текущую верификацию при добавлении в whitelist."""
        try:
            if not user_id and username:
                user = await self.db_manager.users.get_by_username(username)
                if user:
                    user_id = user.telegram_id
                else:
                    logger.debug(f"Пользователь @{username} не найден в БД для автозавершения верификации")
                    return
            
            if not user_id:
                return
                
            verification = await self.db_manager.user_group_verifications.get_by_user_and_group(user_id, group_id)
            
            if verification and not verification.verified:
                await self.db_manager.user_group_verifications.update_verified_status(user_id, group_id, True, "whitelist")
                await self.db_manager.user_group_verifications.update_requires_verification(user_id, group_id, False)
                
                identifier = f"@{username}" if username else str(user_id)
                logger.info(f"Автоматически завершена верификация для пользователя {identifier} (добавлен в whitelist)")
                
        except Exception as e:
            identifier = f"@{username}" if username else str(user_id)
            logger.error(f"Ошибка автозавершения верификации для {identifier}: {e}")
