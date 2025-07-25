"""Обработчик команды /checkin для переключения режима проверки существующих участников."""

import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from loguru import logger

from bot.database.manager import DatabaseManager
from config.settings import settings

checkin_router = Router(name="checkin_router")
checkin_router.message.filter(F.chat.type.in_(["group", "supergroup"]))


@checkin_router.message(Command("checkin"))
async def checkin_command(message: Message, db_manager: DatabaseManager):
    """
    Команда для переключения режима проверки существующих участников группы.
    Доступна только администраторам группы.
    """
    if not message.from_user:
        return

    user_id = message.from_user.id
    group_id = message.chat.id
    is_anonymous_admin = False

    try:
        if message.from_user.is_bot and message.from_user.username == "GroupAnonymousBot":
            is_anonymous_admin = True
            is_global_admin = False
            is_group_admin = True
        else:
            is_global_admin = user_id in settings.admin_user_ids
            is_group_admin = False

            if not is_global_admin:
                try:
                    chat_member = await message.bot.get_chat_member(group_id, user_id)
                    is_group_admin = chat_member.status in ["administrator", "creator"]
                except Exception as e:
                    logger.error(f"Ошибка проверки прав администратора: {e}")
                    try:
                        await message.bot.send_message(user_id, "❌ Ошибка при проверке прав доступа")
                    except:
                        error_message = await message.reply("❌ Ошибка при проверке прав доступа")
                        asyncio.create_task(_delete_checkin_messages(message, error_message))
                    return

        if not (is_global_admin or is_group_admin):
            logger.debug(f"Пользователь {user_id} попытался использовать команду /checkin в группе {group_id} без прав администратора")
            return

        group = await db_manager.groups.get_by_id(group_id)
        if not group or not group.is_active:
            if is_anonymous_admin:
                error_message = await message.reply("❌ Группа не зарегистрирована в системе")
                asyncio.create_task(_delete_checkin_messages(message, error_message))
            else:
                try:
                    await message.bot.send_message(user_id, "❌ Группа не зарегистрирована в системе")
                except:
                    error_message = await message.reply("❌ Группа не зарегистрирована в системе")
                    asyncio.create_task(_delete_checkin_messages(message, error_message))
            return

        new_mode = await db_manager.groups.toggle_checkin_mode(group_id)

        if new_mode:
            response = (
                "✅ <b>Режим проверки включен</b>\n\n"
                "Теперь существующие участники при отправке сообщений будут "
                "получать напоминания о необходимости верификации.\n\n"
                "❗️ Сообщения УДАЛЯЮТСЯ до прохождения верификации\n"
                "⚠️ После 3+ сообщений без верификации - автоматический бан\n"
                f"⏰ Время на начало верификации: {settings.format_verification_start_timeout()}\n\n"
                "🔄 Повторный вызов /checkin отключит режим"
            )
        else:
            response = (
                "🔴 <b>Режим проверки отключен</b>\n\n"
                "Существующие участники могут писать без ограничений.\n"
                "Новые участники проходят стандартную верификацию."
            )

        if is_anonymous_admin:
            sent_message = await message.reply(response, parse_mode="HTML")
            asyncio.create_task(_delete_checkin_messages(message, sent_message))
        else:
            try:
                await message.bot.send_message(user_id, response, parse_mode="HTML")
                sent_message = await message.reply("✅ Настройки обновлены. Подробности отправлены в личные сообщения.")
                asyncio.create_task(_delete_checkin_messages(message, sent_message))
            except Exception as pm_error:
                logger.warning(f"Не удалось отправить сообщение администратору {user_id} в личку: {pm_error}")
                sent_message = await message.reply(response, parse_mode="HTML")
                asyncio.create_task(_delete_checkin_messages(message, sent_message))
        
        admin_name = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
        logger.info(
            f"Режим checkin {'включен' if new_mode else 'отключен'} "
            f"в группе {group_id} администратором {user_id} ({admin_name})"
        )

    except Exception as e:
        logger.error(f"Ошибка выполнения команды /checkin: {e}")
        if is_anonymous_admin:
            error_message = await message.reply("❌ Произошла ошибка при выполнении команды")
            asyncio.create_task(_delete_checkin_messages(message, error_message))
        else:
            try:
                await message.bot.send_message(user_id, "❌ Произошла ошибка при выполнении команды")
            except:
                error_message = await message.reply("❌ Произошла ошибка при выполнении команды")
                asyncio.create_task(_delete_checkin_messages(message, error_message))


async def _delete_checkin_messages(original_message: Message, response_message: Message):
    """Удаляет сообщения команды checkin через 5 секунд."""
    await asyncio.sleep(5)
    try:
        await response_message.delete()
        await original_message.delete()
    except Exception:
        pass
