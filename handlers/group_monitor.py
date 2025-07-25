"""Хендлер мониторинга группы для автоматической верификации."""

from aiogram import Router, F
from aiogram.filters import ChatMemberUpdatedFilter, IS_MEMBER, IS_NOT_MEMBER
from aiogram.types import (
    ChatMemberUpdated,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from loguru import logger
import asyncio

from bot.middleware.services import DatabaseManager
from bot.database.models.user import User
from bot.services.admin_service import AdminService
from bot.services.group_service import GroupService
from bot.services.verification_service import VerificationService
from bot.services.whitelist_service import WhitelistService
from bot.states.verification import VerificationStates
from config.settings import settings

group_monitor_router = Router(name="group_monitor_router")


@group_monitor_router.chat_member()
async def on_chat_member_updated(event: ChatMemberUpdated, db_manager: DatabaseManager):
    """
    Обрабатывает изменения статуса участников группы, включая назначение/удаление администраторов.
    """
    user = event.new_chat_member.user if event.new_chat_member else event.old_chat_member.user

    logger.debug(f"🔍 DEBUG: chat_member событие получено для пользователя {user.id} в группе {event.chat.id}")

    if user.is_bot:
        logger.debug(f"🤖 Пропускаем бота {user.username}")
        return

    old_status = event.old_chat_member.status if event.old_chat_member else "left"
    new_status = event.new_chat_member.status if event.new_chat_member else "left"

    logger.debug(f"📊 DEBUG: Статусы пользователя {user.id}: {old_status} -> {new_status}")

    if old_status == "left" and new_status == "member":
        logger.info(f"🆕 Новый участник присоединился: {user.full_name} (@{user.username}), ID: {user.id}")
        logger.debug(f"🔄 Вступление {user.id} обрабатывается on_user_joined, пропускаем дублирование")
        return

    if old_status != new_status and old_status != "left" and new_status != "left":
        logger.debug(f"📝 Изменение статуса без вступления/выхода: {user.id} ({old_status} -> {new_status})")

    if old_status != new_status:
        if new_status in ["administrator", "creator"] and old_status not in ["administrator", "creator"]:
            logger.info(
                f"👑 Пользователь {user.full_name} (@{user.username}) назначен администратором в группе {event.chat.id}")
            admin_service = AdminService(db_manager)
            chat_admins = await event.bot.get_chat_administrators(event.chat.id)
            await admin_service.update_group_admins(event.chat.id, chat_admins)

        elif old_status in ["administrator", "creator"] and new_status not in ["administrator", "creator"]:
            logger.info(
                f"👤 Пользователь {user.full_name} (@{user.username}) лишен администраторских прав в группе {event.chat.id}")
            admin_service = AdminService(db_manager)
            chat_admins = await event.bot.get_chat_administrators(event.chat.id)
            await admin_service.update_group_admins(event.chat.id, chat_admins)

    # Обработка случая добавления администратором (не через обычную ссылку)
    if old_status in ["restricted", "kicked"] and new_status == "member":
        logger.info(f"👥 Участник добавлен администратором: {user.full_name} (@{user.username}), ID: {user.id}")
        await _handle_new_member(event, user, db_manager)
        return


@group_monitor_router.chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def on_user_joined(event: ChatMemberUpdated, db_manager: DatabaseManager):
    """
    Обрабатывает вступление нового пользователя в группу через ссылку или поиск.
    """
    logger.debug(f"🔍 DEBUG: on_user_joined обработчик вызван для группы {event.chat.id}")

    user = event.new_chat_member.user
    if user.is_bot:
        logger.debug(f"🤖 on_user_joined: Пропускаем бота {user.username}")
        return

    logger.info(
        f"Новый участник: {user.full_name} (@{user.username}), ID: {user.id}"
    )

    await _handle_new_member(event, user, db_manager)




@group_monitor_router.chat_member(ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER))
async def on_user_left(event: ChatMemberUpdated, db_manager: DatabaseManager):
    """
    Обрабатывает выход пользователя из группы.
    """
    user = event.old_chat_member.user
    if user.is_bot:
        return

    logger.info(
        f"Пользователь покинул группу: {user.full_name} (@{user.username}), ID: {user.id}"
    )


async def _handle_new_member(event: ChatMemberUpdated, user, db_manager: DatabaseManager):
    """Обрабатывает вступление нового пользователя в группу."""
    try:
        chat_member = await event.bot.get_chat_member(event.chat.id, user.id)
        if chat_member.status in ["administrator", "creator"]:
            logger.info(f"Администратор {user.full_name} присоединился. Верификация не требуется.")
            return
    except Exception as e:
        logger.warning(f"Не удалось проверить статус администратора для {user.id}: {e}")

    whitelist_service = WhitelistService(db_manager)
    if await whitelist_service.check_user_in_whitelist(user.id, user.username, event.chat.id):
        await whitelist_service.auto_verify_whitelist_user(user.id, user.username, event.chat.id)
        logger.info(
            f"Пользователь {user.full_name} (@{user.username}) из whitelist группы {event.chat.id} автоматически верифицирован."
        )
        return

    logger.info(f"Новый пользователь {user.id} добавлен, требует верификации")

    await _send_welcome_and_verification(event, user, db_manager)


async def _send_welcome_and_verification(
    event: ChatMemberUpdated, user, db_manager: DatabaseManager
):
    """Отправляет приветствие и запускает процесс верификации."""
    verification = await db_manager.user_group_verifications.get_by_user_and_group(user.id, event.chat.id)
    if verification and verification.verified:
        logger.info(f"Пользователь {user.id} уже верифицирован в группе {event.chat.id}. Пропускаем.")
        return

    db_user = await db_manager.users.get_user_by_telegram_id(user.id)
    if not db_user:
        user_model = User.from_aiogram(user)
        await db_manager.users.add_user(user_model)
    else:
        if user.username != db_user.username:
            await db_manager.users.update_username(user.id, user.username)

    if not verification:
        # Создаем запись для нового участника с пометкой requires_verification=True
        await db_manager.user_group_verifications.create_for_new_member(user.id, event.chat.id)
        logger.info(
            f"Создана запись верификации для НОВОГО участника {user.id} в группе {event.chat.id} (requires_verification=True)")
    else:
        # Если запись уже существует, помечаем как требующего верификации
        await db_manager.user_group_verifications.update_requires_verification(user.id, event.chat.id, True)
        logger.info(f"Помечен как требующий верификации существующий пользователь {user.id} в группе {event.chat.id}")

    await db_manager.user_group_verifications.update_state(
        user.id, event.chat.id, VerificationStates.waiting_for_start.state
    )

    try:
        bot_username = (await event.bot.get_me()).username
        welcome_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🩺 Начать верификацию",
                        url=f"https://t.me/{bot_username}?start=verify_{event.chat.id}"
                    )
                ]
            ]
        )
    except Exception as e:
        logger.error(f"Ошибка получения username бота: {e}")
        welcome_keyboard = None

    try:
        welcome_msg = await event.bot.send_message(
            event.chat.id,
            f"👋 Добро пожаловать, @{user.username or user.first_name}!\n\n"
            f"🩺 Для участия в группе необходимо пройти верификацию медицинского работника.\n"
            f"📱 Проверьте личные сообщения с ботом для начала верификации.\n\n"
            f"⏰ У вас есть {settings.format_verification_start_timeout()}, иначе вы будете исключены из группы.",
            reply_markup=welcome_keyboard,
            reply_to_message_id=None
        )
        logger.info(f"Отправлено приветствие в группу для пользователя {user.id}")

        asyncio.create_task(_delete_welcome_message(event.bot, event.chat.id, welcome_msg.message_id))

    except Exception as e:
        logger.error(f"Ошибка отправки приветствия в группу: {e}")

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🩺 Начать верификацию",
                    callback_data=f"start_verification:{event.chat.id}"
                )
            ]
        ]
    )

    try:
        await event.bot.send_message(
            user.id,
            "👋 <b>Добро пожаловать!</b>\n\n"
            "Вы присоединились к группе медицинских работников. "
            "Для продолжения участия необходимо пройти верификацию.\n\n"
            f"🔹 У вас есть {settings.format_verification_start_timeout()} для начала верификации\n"
            "🔹 После этого времени вы будете автоматически исключены из группы\n\n"
            "Нажмите кнопку ниже чтобы начать процесс верификации:",
            reply_markup=keyboard
        )
        logger.info(f"Приглашение к верификации отправлено пользователю {user.id}.")

        asyncio.create_task(_schedule_user_removal(event.bot, user.id, db_manager, event.chat.id))

    except Exception as e:
        logger.error(f"Не удалось отправить сообщение пользователю {user.id}: {e}")

        try:
            bot_username = (await event.bot.get_me()).username
            warning_msg = await event.bot.send_message(
                event.chat.id,
                f"⚠️ @{user.username or user.first_name}, для прохождения верификации:\n\n"
                f"👆 [Кликните для верификации](https://t.me/{bot_username}?start=verify_{event.chat.id})\n\n"
                f"⏰ У вас есть {settings.format_verification_start_timeout()}, иначе вы будете исключены из группы.",
                reply_to_message_id=None,
                parse_mode="Markdown"
            )
            logger.info(f"Отправлено предупреждение в группу для пользователя {user.id}")

            asyncio.create_task(_delete_welcome_message(event.bot, event.chat.id, warning_msg.message_id))

            asyncio.create_task(_schedule_user_removal(event.bot, user.id, db_manager, event.chat.id))

        except Exception as group_error:
            logger.error(f"Не удалось отправить сообщение в группу: {group_error}")


async def _schedule_user_removal(bot, user_id: int, db_manager: DatabaseManager, group_id: int = None):
    """Планирует удаление пользователя если он не начал верификацию."""
    await asyncio.sleep(settings.verification_start_timeout_hours * 3600)

    try:
        if not settings.auto_delete_unverified:
            logger.info(f"Автоудаление отключено, пропускаем пользователя {user_id}")
            return

        if group_id:
            verification = await db_manager.user_group_verifications.get_by_user_and_group(user_id, group_id)
            if verification and (verification.verified or (verification.state and verification.state not in ['waiting_for_start', None])):
                logger.info(
                    f"Пользователь {user_id} уже верифицирован или начал верификацию в группе {group_id}, отменяем удаление")
                return

            try:
                await bot.ban_chat_member(group_id, user_id)
                await bot.unban_chat_member(group_id, user_id)
                logger.info(f"Пользователь {user_id} удален из группы {group_id}")

                await db_manager.user_group_verifications.update_state(
                    user_id, group_id, VerificationStates.verification_timeout.state
                )

            except Exception as e:
                logger.error(f"Ошибка удаления пользователя {user_id} из группы {group_id}: {e}")
        else:
            active_groups = await db_manager.groups.get_active()

            for group in active_groups:
                verification = await db_manager.user_group_verifications.get_by_user_and_group(user_id, group.group_id)
                if verification and (verification.verified or (verification.state and verification.state not in ['waiting_for_start', None])):
                    continue

                try:
                    await bot.ban_chat_member(group.group_id, user_id)
                    await bot.unban_chat_member(group.group_id, user_id)
                    logger.info(f"Пользователь {user_id} удален из группы {group.group_id}")

                    await db_manager.user_group_verifications.update_state(
                        user_id, group.group_id, VerificationStates.verification_timeout.state
                    )

                except Exception as e:
                    logger.error(f"Ошибка удаления пользователя {user_id} из группы {group.group_id}: {e}")

        try:
            await bot.send_message(
                user_id,
                "⏰ <b>Время на начало верификации истекло</b>\n\n"
                "К сожалению, вы не начали процесс верификации в течение 5 минут "
                "и были исключены из группы.\n\n"
                "Если хотите присоединиться снова, обратитесь к администратору."
            )
        except Exception:
            pass

        logger.info(f"Пользователь {user_id} удален за неначало верификации в течение 5 минут")

    except Exception as e:
        logger.error(f"Ошибка при удалении пользователя {user_id} по тайм-ауту: {e}")


async def _delete_welcome_message(bot, chat_id: int, message_id: int):
    """Удаляет приветственное сообщение через 2 минуты."""
    await asyncio.sleep(2 * 60)

    try:
        await bot.delete_message(chat_id, message_id)
        logger.info(f"Удалено приветственное сообщение {message_id} в чате {chat_id}")
    except Exception as e:
        logger.debug(f"Не удалось удалить приветственное сообщение {message_id}: {e}")
