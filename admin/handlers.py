import asyncio

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger

from bot.handlers.admin.core import user_is_admin_in_chat
from bot.services.admin_service import AdminService
from config.settings import Settings

# В начало файла добавляем новые импорты
from aiogram.types import ChatMemberUpdated
from aiogram.filters import ChatMemberUpdatedFilter
from aiogram.enums import ChatMemberStatus

# Добавляем новый обработчик в конец файла (перед регистрацией хэндлеров)
@admin_handlers_router.chat_member(
    ChatMemberUpdatedFilter(
        member_status_changed=ChatMemberStatus.LEFT >> ChatMemberStatus.MEMBER
    )
)
async def on_new_member(event: ChatMemberUpdated, admin_service: AdminService, settings: Settings):
    """
    Обрабатывает вступление новых участников в группу.
    Отправляет им приветственное сообщение с просьбой пройти верификацию.
    """
    try:
        # Игнорируем ботов и случаи, когда бот сам добавляется в группу
        if event.new_chat_member.user.is_bot or event.new_chat_member.user.id == event.bot.id:
            return

        # Проверяем, что событие произошло в группе/супергруппе
        if event.chat.type not in ["group", "supergroup"]:
            return

        # Проверяем, что пользователь еще не прошел верификацию
        if await admin_service.is_user_verified(event.new_chat_member.user.id, event.chat.id):
            return

        try:
            # Пытаемся отправить сообщение в ЛС
            await event.bot.send_message(
                chat_id=event.new_chat_member.user.id,
                text=f"👋 Привет, {event.new_chat_member.user.first_name}!\n\n"
                     f"Чтобы писать в группе {event.chat.title}, тебе нужно пройти верификацию.\n\n"
                     f"Нажми /verify в этой группе, чтобы начать."
            )
        except Exception as e:
            logger.warning(f"Не удалось отправить сообщение пользователю {event.new_chat_member.user.id}: {e}")
            # Если не получилось отправить в ЛС, пишем в группу (если бот имеет права)
            if await user_is_admin_in_chat(
                await event.bot.me(), event.chat.id, admin_service, settings, event.bot
            ):
                msg = await event.chat.send_message(
                    f"{event.new_chat_member.user.mention_html()}, "
                    f"для доступа к чату тебе нужно пройти верификацию. Нажми /verify",
                    parse_mode="HTML"
                )
                # Удаляем сообщение через 1 минуту
                asyncio.create_task(_delete_message_later(msg))
    except Exception as e:
        logger.error(f"Ошибка в обработчике нового участника: {e}", exc_info=True)


async def _delete_message_later(message: Message, delay: int = 60):
    """Удаляет сообщение через указанное количество секунд"""
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass

admin_handlers_router = Router(name="admin_handlers")


def get_admin_panel_keyboard(group_id: int) -> InlineKeyboardBuilder:
    """Возвращает клавиатуру админ-панели с group_id в колбэках."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Управление Whitelist",
        callback_data=f"admin:whitelist:manage:{group_id}",
    )
    builder.adjust(1)
    return builder


@admin_handlers_router.message(Command("admin"), F.chat.type.in_(["group", "supergroup"]))
async def admin_command_in_group(
    message: Message, admin_service: AdminService, settings: Settings
):
    """
    Обрабатывает команду /admin в групповых чатах.
    Доступно администраторам группы.
    """
    try:
        is_admin = await user_is_admin_in_chat(
            message.from_user, message.chat.id, admin_service, settings, message.bot
        )

        if not is_admin:
            logger.debug(
                f"❌ Пользователь {message.from_user.id} не является администратором группы {message.chat.id}")
            return


        admin_text = "🔧 <b>Административная панель</b>"
        keyboard = get_admin_panel_keyboard(message.chat.id).as_markup()

        # Проверяем, не является ли отправитель анонимным администратором
        if message.from_user.is_bot and message.from_user.username == "GroupAnonymousBot":
            bot_username = (await message.bot.get_me()).username
            warning_msg = await message.reply(
                f"🔧 **Админ-панель**\n\n"
                f"👆 [Открыть панель управления](https://t.me/{bot_username}?start=admin_{message.chat.id})",
                parse_mode="Markdown"
            )
            asyncio.create_task(_delete_admin_messages(message, warning_msg))
            return

        try:
            await message.bot.send_message(
                chat_id=message.from_user.id,
                text=f"{admin_text} для группы <b>{message.chat.title}</b>.",
                reply_markup=keyboard,
            )

            sent_message = await message.reply(
                "✅ Панель управления отправлена вам в личные сообщения."
            )
            await asyncio.sleep(5)
            await sent_message.delete()
            await message.delete()

        except TelegramBadRequest as e:
            logger.warning(f"⚠️ Не удалось отправить личное сообщение пользователю {message.from_user.id}: {e}")

            bot_username = (await message.bot.get_me()).username
            warning_msg = await message.reply(
                f"⚠️ @{message.from_user.username or message.from_user.first_name}, "
                f"для доступа к админ-панели:\n\n"
                f"👆 [Кликните для открытия админ-панели](https://t.me/{bot_username}?start=admin_{message.chat.id})\n\n"
                f"💡 После перехода по ссылке используйте команду /admin снова в группе.",
                parse_mode="Markdown"
            )

            # Удаляем сообщения через некоторое время
            asyncio.create_task(_delete_admin_messages(message, warning_msg))

    except Exception as e:
        logger.error(f"❌ Критическая ошибка в обработчике админ-команды: {e}", exc_info=True)
        try:
            error_message = await message.reply("❌ Произошла ошибка при обработке команды.")
            if message.chat.type in ["group", "supergroup"]:
                asyncio.create_task(_delete_admin_messages(message, error_message))
        except Exception:
            pass


async def _delete_admin_messages(original_message: Message, warning_message: Message):
    """Удаляет сообщения через 30 секунд."""
    await asyncio.sleep(30)
    try:
        await warning_message.delete()
        await original_message.delete()
    except Exception:
        pass


@admin_handlers_router.message(Command(commands=["admin"]), F.chat.type == "private")
async def admin_command_in_private(message: Message, settings: Settings, admin_service: AdminService):
    """
    Обрабатывает команду /admin в личных сообщениях.
    Информирует пользователя о необходимости использовать команду в группе.
    Доступно только администраторам.
    """
    user_id = message.from_user.id
    if user_id not in settings.admin_user_ids:
        is_group_admin = await admin_service.is_user_admin_in_any_group(user_id)
        if not is_group_admin:
            await message.answer(
                "❌ У вас нет прав администратора. Эта команда доступна только администраторам групп."
            )
            return

    await message.answer(
        "Для управления ботом используйте команду /admin непосредственно в группе, "
        "где хотите управлять настройками.\n\n"
        "Административная панель будет отправлена вам в личные сообщения "
        "с привязкой к выбранной группе."
    )


@admin_handlers_router.message(CommandStart(deep_link=True, magic=F.args.startswith("admin_")))
async def admin_deep_link_handler(message: Message, admin_service: AdminService, settings: Settings):
    """
    Обрабатывает переходы по ссылке /start admin_group_id.
    Отправляет админ-панель для указанной группы.
    """
    try:
        # Извлекаем group_id из deep link
        group_id = int(message.text.split("admin_")[1])

        # Проверяем права администратора
        is_admin = await user_is_admin_in_chat(
            message.from_user, group_id, admin_service, settings, message.bot
        )

        if not is_admin:
            await message.answer(
                "❌ У вас нет прав администратора в указанной группе."
            )
            return

        # Получаем информацию о группе
        try:
            chat = await message.bot.get_chat(group_id)
            group_name = chat.title
        except Exception:
            group_name = "Неизвестная группа"

        # Отправляем админ-панель
        admin_text = "🔧 <b>Административная панель</b>"
        keyboard = get_admin_panel_keyboard(group_id).as_markup()

        await message.answer(
            f"{admin_text} для группы <b>{group_name}</b>.\n\n"
            f"✅ Теперь вы можете управлять настройками бота для этой группы.",
            reply_markup=keyboard
        )

    except (ValueError, IndexError):
        await message.answer(
            "❌ Неверная ссылка. Используйте команду /admin в группе."
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке admin deep link: {e}")
        await message.answer(
            "❌ Произошла ошибка. Попробуйте использовать команду /admin в группе."
        )
