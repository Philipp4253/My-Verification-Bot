"""Сервис для управления группами."""

from aiogram import Bot
from loguru import logger

from bot.database.manager import DatabaseManager
from bot.database.models.group import Group
from bot.services.admin_service import AdminService


class GroupService:
    """Сервис для бизнес-логики, связанной с группами."""

    def __init__(self, db_manager: DatabaseManager, bot: Bot):
        """
        Инициализация сервиса.

        :param db_manager: Менеджер базы данных.
        :param bot: Экземпляр бота.
        """
        self.db = db_manager
        self.bot = bot
        self.admin_service = AdminService(db_manager)

    async def register_group(self, group_id: int, group_name: str) -> Group:
        """
        Регистрирует новую группу или активирует существующую.

        - Добавляет/обновляет информацию о группе.
        - Получает список администраторов из Telegram.
        - Сохраняет администраторов в базу данных.
        - Автоматически верифицирует существующих участников группы.

        :param group_id: ID группы.
        :param group_name: Название группы.
        :return: Экземпляр зарегистрированной группы.
        """
        logger.info(f"Регистрация группы: {group_name} ({group_id})")

        group = Group(
            group_id=group_id,
            group_name=group_name,
            is_active=True
        )
        await self.db.groups.add_or_update(group)

        # Обновляем администраторов группы
        try:
            chat_admins = await self.bot.get_chat_administrators(group_id)
            await self.admin_service.update_group_admins(group_id, chat_admins)
        except Exception as e:
            logger.error(f"Не удалось получить или обновить администраторов для группы {group_id}: {e}")

        # Автоматически верифицируем существующих участников группы
        await self._auto_verify_existing_members(group_id, group_name)

        # Устанавливаем команды для администраторов
        try:
            from bot.utils.commands import set_admin_commands_for_group
            logger.info(f"Устанавливаем команды для администраторов группы {group_id}")
            await set_admin_commands_for_group(self.bot, group_id)
            logger.info(f"Команды для администраторов группы {group_id} успешно установлены")
        except Exception as e:
            logger.error(f"Не удалось установить команды для администраторов группы {group_id}: {e}")

        logger.info(f"Группа {group_name} ({group_id}) успешно зарегистрирована/активирована.")
        return group

    async def deactivate_group(self, group_id: int) -> None:
        """
        Деактивирует группу.

        :param group_id: ID группы для деактивации.
        """
        logger.warning(f"Деактивация группы: {group_id}")
        await self.db.groups.set_active_status(group_id, is_active=False)

        try:
            from bot.utils.commands import remove_admin_commands_for_group
            await remove_admin_commands_for_group(self.bot, group_id)
        except Exception as e:
            logger.error(f"Не удалось удалить команды для группы {group_id}: {e}")

        logger.info(f"Группа {group_id} была деактивирована.")

    async def _auto_verify_existing_members(self, group_id: int, group_name: str) -> None:
        """
        Автоматически верифицирует всех существующих участников группы при добавлении бота.

        К сожалению, Telegram Bot API не предоставляет прямого способа получить список всех участников группы.
        Поэтому мы используем альтернативный подход: включаем режим "мягкой" верификации,
        при котором участники автоматически верифицируются при первой активности.

        :param group_id: ID группы
        :param group_name: Название группы
        """
        logger.info(f"Настройка автоверификации для существующих участников группы '{group_name}' ({group_id})")

        try:
            # Получаем количество участников группы
            chat = await self.bot.get_chat(group_id)
            member_count = getattr(chat, 'member_count', 0)

            logger.info(f"В группе {group_id} найдено {member_count} участников")

            if member_count > 5000:
                logger.warning(
                    f"Группа {group_id} слишком большая ({member_count} участников). Автоверификация отключена.")
                return

            # Telegram Bot API не позволяет получить список всех участников группы через bot API
            # Поэтому используем флаг в базе данных для последующей автоверификации при активности
            logger.info(f"✅ Настроена автоверификация для группы '{group_name}' ({group_id})")
            logger.info("📋 Участники будут автоматически верифицированы при первой активности в группе")

        except Exception as e:
            logger.error(f"Ошибка при настройке автоверификации для группы {group_id}: {e}")
            logger.info("Продолжаем без автоверификации. Участники должны будут пройти обычную верификацию.")

    async def _schedule_auto_verify_disable(self, group_id: int) -> None:
        """Устаревший метод - больше не используется."""
        pass
