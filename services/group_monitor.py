"""
Сервис для мониторинга активности в группах.
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from loguru import logger

from config.settings import Settings
from bot.database.manager import DatabaseManager
from bot.database.models.user import User


class GroupMonitorService:
    """Сервис для бизнес-логики, связанной с мониторингом групп."""

    def __init__(self, bot: Bot, db_manager: DatabaseManager, settings: Settings):
        self.bot = bot
        self.db_manager = db_manager
        self.settings = settings
        self._monitoring = False

    async def start_monitoring(self):
        """Запуск мониторинга активности."""
        if self._monitoring:
            logger.warning("Мониторинг уже запущен.")
            return

        self._monitoring = True
        logger.info("Мониторинг активности запущен.")
        while self._monitoring:
            try:
                await self.check_unverified_users()
                await self._check_all_users_in_groups()
                await asyncio.sleep(3600)
            except Exception as e:
                logger.error(f"Ошибка в цикле мониторинга: {e}")
                await asyncio.sleep(300)

    def stop_monitoring(self):
        """Остановка мониторинга активности."""
        self._monitoring = False
        logger.info("Мониторинг активности остановлен.")

    async def check_unverified_users(self):
        """
        Проверяет пользователей, которые не прошли верификацию
        и удаляет их, если время ожидания истекло.
        """
        if not self.settings.auto_delete_unverified:
            logger.debug("Автоматическое удаление неактивных пользователей отключено.")
            return

        timeout_hours = self.settings.verification_complete_timeout_hours
        logger.debug(f"Запуск проверки не верифицированных пользователей (таймаут: {self.settings.format_verification_complete_timeout()})...")

        unverified_users = await self.get_long_unverified_users(timeout_hours)
        if not unverified_users:
            logger.debug("Не найдено пользователей для удаления.")
            return

        logger.info(f"Найдено {len(unverified_users)} пользователей для удаления.")
        for user_id in unverified_users:
            await self.kick_user_from_all_groups(user_id)

    async def get_long_unverified_users(self, timeout_hours: int) -> List[int]:
        """
        Получает список ID пользователей, которые не прошли верификацию
        дольше указанного времени.
        """
        unverified_users = []
        try:
            import aiosqlite
            async with aiosqlite.connect(self.db_manager.db_path) as db:
                async with db.execute("""
                    SELECT user_id FROM users
                    WHERE verified = 0
                    AND created_at <= datetime('now', ?)
                """, (f'-{timeout_hours} hours',)) as cursor:
                    async for row in cursor:
                        user_id = row[0]
                        try:
                            member = await self.bot.get_chat_member(
                                self.settings.telegram_group_id, user_id
                            )
                            if member.status not in ['left', 'kicked']:
                                unverified_users.append(user_id)
                        except (TelegramBadRequest, TelegramForbiddenError):
                            await self.db_manager.users.update_user_state(user_id, "left_group")

        except Exception as e:
            logger.error(f"Ошибка при получении списка не верифицированных пользователей: {e}")

        return unverified_users

    async def kick_user_from_all_groups(self, user_id: int):
        """
        Удаляет пользователя из всех групп, где есть бот.
        В текущей реализации - из одной основной группы.
        """
        group_id = self.settings.telegram_group_id
        try:
            await self.bot.kick_chat_member(chat_id=group_id, user_id=user_id)
            logger.info(
                f"Пользователь {user_id} удален из группы {group_id} за неактивность."
            )
            await self.db_manager.users.update_user_state(user_id, "removed_timeout")

            try:
                await self.bot.send_message(
                    user_id,
                    f"Вы были удалены из группы, так как не прошли верификацию в течение {self.settings.format_verification_complete_timeout()}."
                )
            except (TelegramBadRequest, TelegramForbiddenError):
                logger.warning(f"Не удалось отправить уведомление об удалении пользователю {user_id}")

        except (TelegramBadRequest, TelegramForbiddenError) as e:
            logger.warning(f"Не удалось удалить пользователя {user_id}: {e}")
            await self.db_manager.users.update_user_state(user_id, "removal_failed")
        except Exception as e:
            logger.error(f"Ошибка при удалении пользователя {user_id}: {e}")
