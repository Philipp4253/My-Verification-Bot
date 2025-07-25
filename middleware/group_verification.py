"""Middleware для блокировки сообщений неверифицированных пользователей в группе."""

from typing import Callable, Dict, Any, Awaitable, Set, Union
from datetime import datetime, timedelta

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message
from loguru import logger

from bot.database.manager import DatabaseManager
from bot.services.whitelist_service import WhitelistService
from config.settings import Settings


class GroupVerificationMiddleware(BaseMiddleware):
    """Middleware для блокировки сообщений неверифицированных пользователей."""

    def __init__(self, db_manager: DatabaseManager, settings: Settings):
        """
        Инициализация middleware.

        Args:
            db_manager: Экземпляр менеджера базы данных
            settings: Настройки приложения
        """
        self.db_manager = db_manager
        self.settings = settings
        self.whitelist_service = WhitelistService(db_manager)

        self._verified_users_cache: Set[Union[int, str]] = set()
        self._whitelist_cache: Set[int] = set()
        self._cache_ttl = 300
        self._last_cache_update = datetime.now()

        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Обработка middleware для блокировки сообщений.

        Args:
            handler: Следующий обработчик в цепочке
            event: Событие Telegram
            data: Данные для передачи в обработчик

        Returns:
            Результат выполнения обработчика или None если заблокировано
        """
        if not isinstance(event, Message):
            return await handler(event, data)

        username = f"@{event.from_user.username}" if event.from_user.username else event.from_user.first_name
        logger.info(f"🔍 MIDDLEWARE: Получено сообщение от {event.from_user.id} ({username}) в чате {event.chat.id}")

        group = await self.db_manager.groups.get_by_id(event.chat.id)
        if not group or not group.is_active:
            logger.info(f"🔍 MIDDLEWARE: Пропускаем чат {event.chat.id}, не является активной группой")
            return await handler(event, data)

        if event.from_user.is_bot or not event.from_user:
            return await handler(event, data)

        if event.content_type in ['new_chat_members', 'left_chat_member', 'pinned_message']:
            return await handler(event, data)

        user_id = event.from_user.id

        if user_id in self.settings.admin_user_ids:
            logger.debug(f"👑 Глобальный админ {user_id} (@{event.from_user.username}) пропущен")
            return await handler(event, data)

        try:
            chat_member = await event.bot.get_chat_member(event.chat.id, user_id)
            if chat_member.status in ['administrator', 'creator']:
                logger.debug(f"👑 Админ группы {user_id} (@{event.from_user.username}) пропущен")
                return await handler(event, data)
        except Exception as e:
            logger.debug(f"Не удалось проверить права админа для {user_id}: {e}")

        logger.info(f"🔍 MIDDLEWARE: Проверяем доступ пользователя {user_id}")

        username = event.from_user.username

        is_in_whitelist = await self._check_user_whitelist(user_id, username, event.chat.id)
        if is_in_whitelist:
            await self.whitelist_service.auto_verify_whitelist_user(user_id, username=username)
            self.add_verified_user_to_cache(user_id)
            logger.info(f"✅ Пользователь {user_id} (@{username or 'N/A'}) из whitelist автоматически верифицирован")
            return await handler(event, data)

        is_verified = await self._check_user_verification(user_id, event.chat.id)
        if is_verified:
            logger.debug(f"✅ Верифицированный пользователь {user_id} пропущен")
            return await handler(event, data)
        
        should_block = await self._should_block_message(user_id, event.chat.id)
        if should_block:
            logger.info(f"🚫 MIDDLEWARE: Блокируем сообщение от неверифицированного пользователя {user_id}")
            await self._handle_unverified_user_message(event)
            return None
        else:
            logger.debug(f"🔄 MIDDLEWARE: Передаем сообщение от {user_id} в обработчики (режим checkin или новый участник)")
            result = await handler(event, data)
            logger.debug(f"🔄 MIDDLEWARE: Обработчики завершили работу для {user_id}, результат: {result}")
            return result

    async def _check_user_whitelist(self, user_id: int, username: str = None, group_id: int = None) -> bool:
        """
        Проверяет, находится ли пользователь в whitelist с использованием кэша.

        Args:
            user_id: ID пользователя
            username: Username пользователя

        Returns:
            True если пользователь в whitelist, False иначе
        """
        if datetime.now() - self._last_cache_update > timedelta(seconds=self._cache_ttl):
            self._whitelist_cache.clear()

        if user_id in self._whitelist_cache:
            return True

        try:
            is_in_whitelist = await self.whitelist_service.check_user_in_whitelist(user_id, username, group_id)

            if is_in_whitelist:
                self._whitelist_cache.add(user_id)
                return True

            return False

        except Exception as e:
            logger.error(f"❌ Ошибка проверки whitelist для пользователя {user_id}: {e}")
            return False

    async def _check_user_verification(self, user_id: int, group_id: int = None) -> bool:
        """
        Проверяет верификацию пользователя в конкретной группе с использованием кэша.

        Args:
            user_id: ID пользователя
            group_id: ID группы

        Returns:
            True если пользователь верифицирован в данной группе, False иначе
        """
        if not group_id:
            return False

        cache_key = f"{user_id}_{group_id}"

        if datetime.now() - self._last_cache_update > timedelta(seconds=self._cache_ttl):
            self._verified_users_cache.clear()
            self._last_cache_update = datetime.now()

        if cache_key in self._verified_users_cache:
            return True

        try:
            verification = await self.db_manager.user_group_verifications.get_by_user_and_group(user_id, group_id)

            if verification and verification.verified:
                self._verified_users_cache.add(cache_key)
                return True

            return False

        except Exception as e:
            logger.error(f"❌ Ошибка проверки верификации пользователя {user_id} в группе {group_id}: {e}")
            return False

    async def _should_block_message(self, user_id: int, group_id: int) -> bool:
        """
        Определяет нужно ли блокировать сообщение в middleware.
        
        Args:
            user_id: ID пользователя
            group_id: ID группы
            
        Returns:
            True если нужно блокировать, False если передать в обработчики
        """
        try:
            group = await self.db_manager.groups.get_by_id(group_id)
            if not group:
                return True
                
            verification = await self.db_manager.user_group_verifications.get_by_user_and_group(user_id, group_id)
            
            if verification and verification.requires_verification:
                logger.debug(f"Новый участник {user_id}: блокируем в middleware")
                return True
            elif group.checkin_mode:
                logger.debug(f"Режим checkin включен для {user_id}: передаем в обработчики")
                return False
            else:
                logger.debug(f"Существующий участник {user_id}, режим checkin выключен: пропускаем")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка проверки блокировки для {user_id} в группе {group_id}: {e}")
            return True

    async def _handle_unverified_user_message(self, message: Message):
        """
        Обрабатывает сообщение от неверифицированного пользователя.

        Args:
            message: Сообщение для блокировки
        """
        user_id = message.from_user.id

        try:
            await message.delete()
            logger.info(f"🚫 Удалено сообщение от неверифицированного пользователя {user_id}")

        except Exception as e:
            logger.error(f"❌ Ошибка при обработке сообщения неверифицированного пользователя {user_id}: {e}")

    def invalidate_user_cache(self, user_id: int, group_id: int = None):
        """
        Принудительно очищает кэш для конкретного пользователя в группе.

        Используется когда пользователь проходит верификацию.

        Args:
            user_id: ID пользователя
            group_id: ID группы (если None, очищает для всех групп)
        """
        if group_id:
            cache_key = f"{user_id}_{group_id}"
            self._verified_users_cache.discard(cache_key)
            logger.debug(f"🔄 Очищен кэш для пользователя {user_id} в группе {group_id}")
        else:
            to_remove = [key for key in self._verified_users_cache if key.startswith(f"{user_id}_")]
            for key in to_remove:
                self._verified_users_cache.discard(key)
            logger.debug(f"🔄 Очищен кэш для пользователя {user_id} во всех группах")

    def add_verified_user_to_cache(self, user_id: int, group_id: int = None):
        """
        Добавляет пользователя в кэш верифицированных для конкретной группы.

        Args:
            user_id: ID пользователя
            group_id: ID группы (если None, добавляет только user_id для обратной совместимости)
        """
        if group_id:
            cache_key = f"{user_id}_{group_id}"
            self._verified_users_cache.add(cache_key)
            logger.debug(f"✅ Пользователь {user_id} добавлен в кэш верифицированных для группы {group_id}")
        else:
            self._verified_users_cache.add(user_id)
            logger.debug(f"✅ Пользователь {user_id} добавлен в кэш верифицированных (глобально)")

    def invalidate_whitelist_cache(self, user_id: int):
        """
        Принудительно очищает кэш whitelist для конкретного пользователя.

        Используется когда пользователь добавляется/удаляется из whitelist.

        Args:
            user_id: ID пользователя
        """
        self._whitelist_cache.discard(user_id)
        logger.debug(f"🔄 Очищен кэш whitelist для пользователя {user_id}")

    def add_whitelist_user_to_cache(self, user_id: int):
        """
        Добавляет пользователя в кэш whitelist.

        Args:
            user_id: ID пользователя
        """
        self._whitelist_cache.add(user_id)
        logger.debug(f"✅ Пользователь {user_id} добавлен в кэш whitelist")
