"""
Обработчик событий, связанных с жихненным циклом бота в чатах.
(добавление в чат, удаление из чата)
"""
from aiogram import Router, F
from aiogram.filters.chat_member_updated import ChatMemberUpdatedFilter, KICKED, LEFT, MEMBER, ADMINISTRATOR
from aiogram.types import ChatMemberUpdated
from loguru import logger

from bot.services.group_service import GroupService


bot_lifecycle_router = Router(name="bot_lifecycle_router")


@bot_lifecycle_router.my_chat_member()
async def handle_my_chat_member(event: ChatMemberUpdated, group_service: GroupService):
    """
    Обрабатывает все изменения статуса бота в группах.
    """
    old_status = event.old_chat_member.status if event.old_chat_member else "None"
    new_status = event.new_chat_member.status
    group_id = event.chat.id
    group_name = event.chat.title

    logger.info(f"🔄 Изменение статуса бота: {old_status} -> {new_status} в '{group_name}' ({group_id})")

    if new_status == "administrator" and old_status != "administrator":
        logger.success(f"🔥 Бот получил права администратора в группе '{group_name}' ({group_id})")
        await group_service.register_group(group_id, group_name)

    elif old_status == "administrator" and new_status in ["kicked", "left", "member"]:
        logger.warning(f"🚫 Бот потерял права администратора в группе '{group_name}' ({group_id})")
        await group_service.deactivate_group(group_id)
