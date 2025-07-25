"""
Основные хендлеры для управления whitelist (меню, список).
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.services.admin_service import AdminService
from bot.services.whitelist_service import WhitelistService
from config.settings import Settings
from .utils import check_admin_permissions, get_whitelist_management_text_and_keyboard

router = Router()


@router.callback_query(F.data.startswith("admin:whitelist:manage:"))
async def show_whitelist_management(
    callback: CallbackQuery,
    admin_service: AdminService,
    whitelist_service: WhitelistService,
    settings: Settings
):
    """Отображает панель управления белым списком."""
    group_id = int(callback.data.split(':')[-1])
    if not await check_admin_permissions(callback, group_id, admin_service, settings):
        return

    text, keyboard = await get_whitelist_management_text_and_keyboard(whitelist_service, group_id)

    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception as e:
        if "message is not modified" not in str(e):
            from loguru import logger
            logger.error(f"Ошибка при обновлении меню whitelist: {e}")

    await callback.answer()


@router.callback_query(F.data.startswith("admin:whitelist:list:"))
async def list_whitelisted_users(
    callback: CallbackQuery,
    admin_service: AdminService,
    whitelist_service: WhitelistService,
    settings: Settings
):
    """Отображает список пользователей в белом списке."""
    group_id = int(callback.data.split(':')[-1])
    if not await check_admin_permissions(callback, group_id, admin_service, settings):
        return

    entries = await whitelist_service.get_whitelist(group_id)

    if not entries:
        text = "📋 <b>Список доверенных пользователей пуст.</b>"
    else:
        text_lines = ["📋 <b>Список доверенных пользователей:</b>"]
        for i, entry in enumerate(entries, 1):
            if entry.user_id:
                user_info = f"ID: <code>{entry.user_id}</code>"
            else:
                user_info = f"@{entry.username}"

            try:
                admin_user = await callback.bot.get_chat_member(callback.message.chat.id, entry.added_by)
                if admin_user.user.username:
                    admin_info = f"@{admin_user.user.username}"
                else:
                    admin_info = admin_user.user.first_name or f"ID: {entry.added_by}"
            except Exception:
                admin_info = f"ID: {entry.added_by}"

            text_lines.append(f"{i}. {user_info} (добавил: {admin_info})")
        text = "\n".join(text_lines)

    keyboard = InlineKeyboardBuilder().button(
        text="⬅️ Назад", callback_data=f"admin:whitelist:manage:{group_id}").as_markup()

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("admin:panel:"))
async def close_admin_panel(callback: CallbackQuery):
    """Закрывает админ-панель (удаляет сообщение)."""
    try:
        await callback.message.delete()
    except Exception:
        await callback.message.edit_text("👋 Админ-панель закрыта.")
    await callback.answer()
