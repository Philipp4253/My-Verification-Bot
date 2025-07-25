import asyncio
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger

from bot.states.verification import VerificationStates
from bot.services.verification_service import VerificationService
from bot.database.manager import DatabaseManager
from config.settings import settings

group_events_router = Router(name="group_events_router")
group_events_router.message.filter(F.chat.type.in_(["group", "supergroup"]))


@group_events_router.message()
async def moderate_unverified_messages(message: Message, db_manager: DatabaseManager):
    """
    Модерирует сообщения в группе с дифференцированной обработкой участников.
    
    Новые участники (requires_verification=True): ВСЕГДА проходят верификацию
    Существующие участники (requires_verification=False): проверяются только при включении checkin
    Автоматически определяет тип участника при первом сообщении.
    Админы группы освобождены от проверки.
    """
    if not message.from_user:
        return
        
    username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
    logger.debug(f"📝 Получено сообщение от {message.from_user.id} ({username}) в группе {message.chat.id}: '{message.text}'")
    
    if message.from_user.is_bot:
        return

    if message.text and message.text.startswith('/'):
        return
    
    try:
        chat_member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
        
        if chat_member.status in ["administrator", "creator"]:
            logger.debug(f"👑 Админ {message.from_user.id} ({username}) может писать без верификации")
            return

        from bot.services.whitelist_service import WhitelistService
        whitelist_service = WhitelistService(db_manager)
        if await whitelist_service.check_user_in_whitelist(message.from_user.id, message.from_user.username, message.chat.id):
            logger.debug(f"⭐ Пользователь из whitelist {username} может писать без верификации")
            return

        verification = await db_manager.user_group_verifications.get_by_user_and_group(
            message.from_user.id,
            message.chat.id
        )

        if not verification:
            from bot.database.models.user import User
            db_user = await db_manager.users.get_user_by_telegram_id(message.from_user.id)
            if not db_user:
                user_model = User.from_aiogram(message.from_user)
                await db_manager.users.add_user(user_model)
            
            verification = await db_manager.user_group_verifications.create_for_existing_member(
                message.from_user.id, message.chat.id
            )
            logger.debug(f"👤 Создана запись для существующего участника {username} (requires_verification=False)")

        if verification.verified:
            logger.debug(f"✅ Сообщение от {username} НЕ удалено - пользователь верифицирован")
            return

        group = await db_manager.groups.get_by_id(message.chat.id)
        checkin_mode = group and group.checkin_mode
        
        should_delete = False
        reason = ""
        
        if checkin_mode:
            should_delete = True
            if verification.requires_verification:
                reason = "новый участник в режиме checkin"
            else:
                reason = "существующий участник в режиме checkin"
            logger.debug(f"🔧 Режим checkin включен: удаляем сообщение от {username}")
        else:
            if verification.requires_verification:
                should_delete = True
                reason = "новый участник"
                logger.debug(f"🆕 Удаляем сообщение от нового участника {username}")
            else:
                logger.debug(f"👥 Пропускаем сообщение от существующего участника {username}")
        
        if should_delete:
            await message.delete()
            
            message_count = await db_manager.message_counts.increment_count(message.from_user.id, message.chat.id)
            logger.debug(f"📊 Удалено сообщение #{message_count} от {message.from_user.id} ({username}): {reason}")
            
            if message_count >= 3 and settings.enable_spam_protection:
                try:
                    await message.bot.ban_chat_member(message.chat.id, message.from_user.id)
                    group_name = group.group_name if group else f"ID {message.chat.id}"
                    logger.warning(f"🚫 Пользователь {username} забанен в группе '{group_name}' за спам ({message_count} сообщений)")
                    
                    await _cleanup_user_data(db_manager, message.from_user.id, message.chat.id)
                    return
                except Exception as ban_error:
                    logger.error(f"❌ Не удалось забанить пользователя {message.from_user.id}: {ban_error}")
            elif message_count >= 3:
                logger.debug(f"⚠️ Пользователь {username} написал {message_count} сообщений, но спам-защита отключена")
            
            await _send_verification_reminder(message, db_manager)
        else:
            if verification.verified:
                logger.debug(f"✅ Сообщение от {username} НЕ удалено - пользователь верифицирован")
            else:
                logger.debug(f"✅ Сообщение от {username} НЕ удалено - существующий участник при отключенном checkin")

    except Exception as e:
        logger.error(f"Ошибка при проверке статуса пользователя {message.from_user.id} в группе {message.chat.id}: {e}")


async def _send_verification_reminder(message: Message, db_manager: DatabaseManager):
    """Отправляет напоминание о необходимости верификации."""
    try:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🩺 Начать верификацию", 
                callback_data=f"start_verification:{message.chat.id}"
            )]
        ])
        
        group = await db_manager.groups.get_by_id(message.chat.id)
        group_name = group.group_name if group else "группа"
        
        await message.bot.send_message(
            message.from_user.id,
            f"🏥 <b>Требуется верификация</b>\n\n"
            f"Ваше сообщение в группе \"{group_name}\" было удалено.\n\n"
            f"Для участия в группе необходимо пройти верификацию медицинского работника.\n\n"
            f"Нажмите кнопку ниже, чтобы начать верификацию:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        logger.info(f"Отправлено напоминание о верификации пользователю {message.from_user.id}")
        
    except Exception as e:
        try:
            bot_username = (await message.bot.get_me()).username
            username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
            
            fallback_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🩺 Начать верификацию", 
                    url=f"https://t.me/{bot_username}?start=verify_{message.chat.id}"
                )]
            ])
            
            warning_msg = await message.bot.send_message(
                message.chat.id,
                f"⚠️ {username}, для участия в группе необходимо пройти верификацию.\n\n"
                f"⏰ У вас есть 7 дней, иначе вы будете исключены из группы.",
                reply_markup=fallback_keyboard,
                parse_mode="HTML"
            )
            logger.info(f"Отправлено предупреждение в группу для пользователя {message.from_user.id}")
            
            asyncio.create_task(_delete_message_after_delay(message.bot, message.chat.id, warning_msg.message_id, 60))
            
        except Exception as group_error:
            logger.error(f"Не удалось отправить напоминание о верификации пользователю {message.from_user.id}: {e}, {group_error}")


async def _delete_message_after_delay(bot, chat_id: int, message_id: int, delay_seconds: int):
    """Удаляет сообщение после указанной задержки."""
    try:
        await asyncio.sleep(delay_seconds)
        await bot.delete_message(chat_id, message_id)
        logger.debug(f"🗑️ Автоудаление: сообщение {message_id} удалено из чата {chat_id}")
    except Exception as e:
        logger.debug(f"⚠️ Не удалось автоудалить сообщение {message_id} из чата {chat_id}: {e}")


async def _cleanup_user_data(db_manager: DatabaseManager, user_id: int, group_id: int):
    """Очищает все данные пользователя для конкретной группы."""
    try:
        await db_manager.user_group_verifications.delete_by_user_and_group(user_id, group_id)
        await db_manager.message_counts.reset_count(user_id, group_id)
        logger.debug(f"🧹 Очищены данные пользователя {user_id} для группы {group_id}")
    except Exception as e:
        logger.error(f"❌ Ошибка очистки данных пользователя {user_id} в группе {group_id}: {e}")
