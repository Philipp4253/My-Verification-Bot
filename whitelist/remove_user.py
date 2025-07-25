"""
Хендлеры для удаления пользователей из whitelist.
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.services.admin_service import AdminService
from bot.services.whitelist_service import WhitelistService
from config.settings import Settings
from bot.states.admin_states import WhitelistStates
from .utils import check_admin_permissions, get_whitelist_management_text_and_keyboard

router = Router()


@router.callback_query(F.data.startswith("admin:whitelist:remove:"))
async def start_remove_user(callback: CallbackQuery, state: FSMContext, admin_service: AdminService, settings: Settings, db_manager, **kwargs):
    group_id = int(callback.data.split(':')[-1])
    if not await check_admin_permissions(callback, group_id, admin_service, settings):
        return

    try:
        group = await db_manager.groups.get_by_id(group_id)
        group_title = group.group_name if group else f"Группа {group_id}"

        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🆔 Ввести ID", callback_data=f"whitelist:remove_id:{group_id}")
        keyboard.button(text="👤 Ввести @username", callback_data=f"whitelist:remove_username:{group_id}")
        keyboard.button(text="❌ Отмена", callback_data=f"admin:whitelist:manage:{group_id}")
        keyboard.adjust(2, 1)

        if callback.message.chat.type == "private":
            await callback.message.edit_text(
                "➖ <b>Удаление из белого списка</b>\n\n"
                f"📍 Группа: {group_title}\n\n"
                "Выберите способ удаления:",
                reply_markup=keyboard.as_markup()
            )
        else:
            await callback.bot.send_message(
                callback.from_user.id,
                "➖ <b>Удаление из белого списка</b>\n\n"
                f"📍 Группа: {group_title}\n\n"
                "Выберите способ удаления:",
                reply_markup=keyboard.as_markup()
            )

            await callback.message.edit_text(
                "➖ <b>Удаление пользователя</b>\n\n"
                "📩 Проверьте личные сообщения с ботом для выбора способа удаления."
            )

        await callback.answer()

    except Exception:
        await callback.answer("❌ Не удалось отправить сообщение в ЛС. Убедитесь, что вы начали диалог с ботом.", show_alert=True)


@router.callback_query(F.data.startswith("whitelist:remove_id:"))
async def handle_remove_input_id(callback: CallbackQuery, state: FSMContext, admin_service: AdminService, settings: Settings):
    group_id = int(callback.data.split(':')[-1])
    if not await check_admin_permissions(callback, group_id, admin_service, settings):
        return

    await state.set_state(WhitelistStates.removing_user)
    await state.update_data(group_id=group_id, input_type="id")

    await callback.message.edit_text(
        "🆔 <b>Введите ID пользователя для удаления:</b>\n\n"
        "Пример: 123456789",
        reply_markup=InlineKeyboardBuilder().button(
            text="❌ Отмена", callback_data=f"admin:whitelist:manage:{group_id}"
        ).as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("whitelist:remove_username:"))
async def handle_remove_input_username(callback: CallbackQuery, state: FSMContext, admin_service: AdminService, settings: Settings):
    group_id = int(callback.data.split(':')[-1])
    if not await check_admin_permissions(callback, group_id, admin_service, settings):
        return

    await state.set_state(WhitelistStates.removing_user)
    await state.update_data(group_id=group_id, input_type="username")

    await callback.message.edit_text(
        "👤 <b>Введите username пользователя для удаления:</b>\n\n"
        "Пример: @username или username",
        reply_markup=InlineKeyboardBuilder().button(
            text="❌ Отмена", callback_data=f"admin:whitelist:manage:{group_id}"
        ).as_markup()
    )
    await callback.answer()


@router.message(WhitelistStates.removing_user, F.text, F.chat.type == "private")
async def process_remove_user(
    message: Message,
    state: FSMContext,
    admin_service: AdminService,
    whitelist_service: WhitelistService,
    settings: Settings
):
    data = await state.get_data()
    group_id = data.get("group_id")
    input_type = data.get("input_type", "auto")

    if not await check_admin_permissions(message, group_id, admin_service, settings):
        await state.clear()
        return

    user_input = message.text.strip()
    user_id_to_remove = None
    username_to_remove = None

    if input_type == "id":
        try:
            user_id_to_remove = int(user_input)
        except ValueError:
            await message.answer("❌ Ошибка: Введите корректный числовой ID.")
            return
    elif input_type == "username":
        username_to_remove = user_input.lstrip('@')
        if not username_to_remove:
            await message.answer("❌ Ошибка: Введите корректный username.")
            return
    else:
        if user_input.startswith('@'):
            username_to_remove = user_input[1:]
        else:
            try:
                user_id_to_remove = int(user_input)
            except ValueError:
                await message.answer("❌ Ошибка: Введите корректный ID (число) или username (с @).")
                return

    try:
        entries = await whitelist_service.get_whitelist(group_id)
        user_to_remove = None

        if user_id_to_remove:
            user_to_remove = next((e for e in entries if e.user_id == user_id_to_remove), None)
        elif username_to_remove:
            user_to_remove = next((e for e in entries if e.username == username_to_remove), None)

        if not user_to_remove:
            identifier = f"@{username_to_remove}" if username_to_remove else str(user_id_to_remove)
            status_message = f"Пользователь {identifier} не найден в белом списке."
        else:
            if user_to_remove.user_id:
                success = await whitelist_service.remove_from_whitelist(group_id, user_to_remove.user_id)
            else:
                success = await whitelist_service.remove_by_entry_id(user_to_remove.id)

            identifier = f"@{user_to_remove.username}" if user_to_remove.username else f"ID: {user_to_remove.user_id}"
            status_message = f"Пользователь {identifier} успешно удален из белого списка." if success else f"Не удалось удалить пользователя {identifier}."

    except Exception as e:
        status_message = f"Ошибка при удалении: {str(e)}"

    try:
        text, keyboard = await get_whitelist_management_text_and_keyboard(
            whitelist_service, group_id, status_message=status_message
        )
        await message.answer(text, reply_markup=keyboard)
        await state.clear()
    except Exception as e:
        await message.answer(f"✅ {status_message}")
        await state.clear()
