"""Module for setting up bot commands."""
import logging
from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeAllPrivateChats, BotCommandScopeAllGroupChats, BotCommandScopeChatAdministrators
from aiogram.exceptions import TelegramBadRequest

logger = logging.getLogger(__name__)


async def set_bot_commands(bot: Bot):
    """
    Sets up the commands for the bot in the Telegram UI.

    This function clears any previously set commands and then configures
    commands to be visible only in private chats with the bot.
    """
    try:
        await bot.delete_my_commands(scope=BotCommandScopeDefault())
        await bot.delete_my_commands(scope=BotCommandScopeAllPrivateChats())
        await bot.delete_my_commands(scope=BotCommandScopeAllGroupChats())
        logger.info("Старые команды бота очищены для всех scope")
    except TelegramBadRequest as e:
        logger.warning(f"Ошибка при очистке команд: {e}")

    private_commands = [
        BotCommand(command="start", description="Верификация"),
        BotCommand(command="admin", description="Админ-панель"),
    ]
    
    group_commands = [
        BotCommand(command="admin", description="Админ-панель"),
    ]

    try:
        await bot.set_my_commands(private_commands, scope=BotCommandScopeAllPrivateChats())
        logger.info("Команды бота настроены для личных сообщений")

        await bot.set_my_commands([], scope=BotCommandScopeAllGroupChats())
        logger.info("Команды удалены из групповых чатов (будут установлены для админов отдельно)")
    except TelegramBadRequest as e:
        logger.error(f"Не удалось установить команды бота: {e}")


async def set_admin_commands_for_group(bot: Bot, group_id: int):
    """
    Устанавливает команды только для администраторов конкретной группы.
    """
    admin_commands = [
        BotCommand(command="admin", description="Админ-панель"),
        BotCommand(command="checkin", description="Режим проверки участников"),
    ]
    
    try:
        await bot.set_my_commands(
            admin_commands, 
            scope=BotCommandScopeChatAdministrators(chat_id=group_id)
        )
        logger.info(f"Команды для администраторов установлены в группе {group_id}")
    except TelegramBadRequest as e:
        logger.error(f"Не удалось установить команды для группы {group_id}: {e}")


async def remove_admin_commands_for_group(bot: Bot, group_id: int):
    """
    Удаляет команды администраторов для конкретной группы.
    """
    try:
        await bot.delete_my_commands(
            scope=BotCommandScopeChatAdministrators(chat_id=group_id)
        )
        logger.info(f"Команды администраторов удалены из группы {group_id}")
    except TelegramBadRequest as e:
        logger.error(f"Не удалось удалить команды для группы {group_id}: {e}")
