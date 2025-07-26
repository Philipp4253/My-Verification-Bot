"""Точка входа в приложение бота верификации врачей."""

from loguru import logger
import asyncio
import sys
from pathlib import Path

from bot.app import BotApp
from config.settings import Settings

from aiogram.dispatcher.filters import ChatMemberUpdatedFilter
from aiogram.dispatcher.filters.state import IS_NOT_MEMBER, IS_MEMBER

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
