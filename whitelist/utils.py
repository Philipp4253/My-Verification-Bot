"""
Вспомогательные функции для управления whitelist.
"""
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import Message, CallbackQuery

from bot.services.admin_service import AdminService
from bot.services.whitelist_service import WhitelistService
from bot.handlers.admin.core import is_group_admin
from config.settings import Settings


def get_whitelist_keyboard(group_id: int) -> InlineKeyboardBuilder:
    """Возвращает клавиатуру управления белым списком."""
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить", callback_data=f"admin:whitelist:add:{group_id}")
    builder.button(text="➖ Удалить", callback_data=f"admin:whitelist:remove:{group_id}")
    builder.button(text="📋 Список", callback_data=f"admin:whitelist:list:{group_id}")
    builder.button(text="⬅️ Назад", callback_data=f"admin:panel:{group_id}")
    builder.adjust(2, 1, 1)
    return builder


async def check_admin_permissions(
    target: Message | CallbackQuery,
    group_id: int,
    admin_service: AdminService,
    settings: Settings
) -> bool:
    """Вспомогательная функция для проверки прав администратора."""
    if not await is_group_admin(target.from_user, group_id, admin_service, settings):
        if isinstance(target, CallbackQuery):
            await target.answer("❌ Доступ запрещен", show_alert=True)
        else:
            error_message = await target.reply("❌ Доступ запрещен")
            if target.chat.type in ["group", "supergroup"]:
                import asyncio
                asyncio.create_task(_delete_error_message(target, error_message))
        return False
    return True


async def get_whitelist_management_text_and_keyboard(whitelist_service: WhitelistService, group_id: int, status_message: str = ""):
    """Формирует текст и клавиатуру для панели управления."""
    entries = await whitelist_service.get_whitelist(group_id)
    count = len(entries)
    text = (
        f"✅ <b>Управление Whitelist</b>\n\n"
        f"👥 Доверенных пользователей в этой группе: <b>{count}</b>"
    )
    if status_message:
        text += f"\n\n<i>{status_message}</i>"

    keyboard = get_whitelist_keyboard(group_id).as_markup()
    return text, keyboard


async def _delete_error_message(original_message: Message, error_message: Message):
    """Удаляет сообщения об ошибках через 5 секунд."""
    import asyncio
    await asyncio.sleep(5)
    try:
        await error_message.delete()
        await original_message.delete()
    except Exception:
        pass
