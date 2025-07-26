"""Точка входа в приложение бота верификации врачей."""

from loguru import logger
import asyncio
import sys
from pathlib import Path

from bot.app import BotApp
from config.settings import Settings

from aiogram.dispatcher.filters import ChatMemberUpdatedFilter
from aiogram.dispatcher.filters.state import IS_NOT_MEMBER, IS_MEMBER

# main.py (или аналогичный основной файл)
import asyncio
from datetime import datetime
from aiogram import Bot

from bot.app import BotApp
import asyncio
import logging

logging.basicConfig(level=logging.INFO)

async def main():
    app = BotApp()
    await app.start_polling()

if __name__ == '__main__':
    asyncio.run(main())

async def start_background_tasks(bot: Bot, admin_service: AdminService, settings: Settings):
    """Запуск фоновых задач при старте бота"""
    async def _check_unverified():
        while True:
            try:
                for chat_id in settings.moderated_chats:
                    unverified = await admin_service.get_unverified_users(chat_id)
                    now = datetime.now()
                    
                    for user_id, username, join_date in unverified:
                        if isinstance(join_date, str):
                            join_date = datetime.fromisoformat(join_date)
                        
                        if (now - join_date).total_seconds() > 24 * 3600:  # 24 часа
                            try:
                                await bot.ban_chat_member(chat_id, user_id)
                                await bot.unban_chat_member(chat_id, user_id)
                                await admin_service.remove_user(user_id, chat_id)
                                logger.info(f"Удален {user_id} из {chat_id}")
                            except Exception as e:
                                logger.error(f"Ошибка удаления {user_id}: {e}")
            except Exception as e:
                logger.error(f"Ошибка в фоновой задаче: {e}")
            
            await asyncio.sleep(3600)  # Проверка каждый час

    asyncio.create_task(_check_unverified())

# В функции запуска бота (обычно в конце файла):
async def on_startup(dispatcher, bot: Bot):
    admin_service = AdminService(bot)  # Или как ты инициализируешь сервис
    settings = Settings()  # Твои настройки
    
    # Запускаем фоновые задачи
    await start_background_tasks(bot, admin_service, settings)

if __name__ == '__main__':
    from aiogram import executor
    executor.start_polling(dp, on_startup=on_startup)

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def main() -> None:
    """Главная функция запуска приложения."""
    settings = Settings()
    app = BotApp(settings)

    try:
        await app.start_polling()
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки (Ctrl+C)")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if sys.version_info < (3, 8):
        logger.error("Требуется Python 3.8 или выше")
        sys.exit(1)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Приложение остановлено пользователем")
    except Exception as e:
        logger.error(f"Фатальная ошибка: {e}")
        sys.exit(1)
async def background_tasks(bot: Bot, admin_service: AdminService):
    """Фоновые задачи бота"""
    while True:
        try:
            # Для всех групп из настроек
            for chat_id in settings.moderated_chats:
                removed_count = await admin_service.check_unverified_users(chat_id)
                if removed_count > 0:
                    logger.info(f"Удалено {removed_count} неверифицированных пользователей из {chat_id}")
        except Exception as e:
            logger.error(f"Ошибка в фоновой задаче: {e}")
        
        await asyncio.sleep(3600)  # Проверка каждый час

async def on_startup(bot: Bot, admin_service: AdminService):
    """Действия при запуске бота"""
    asyncio.create_task(background_tasks(bot, admin_service))

