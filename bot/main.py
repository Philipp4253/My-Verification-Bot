"""Точка входа в приложение бота верификации врачей."""
import asyncio
import sys
from pathlib import Path
from loguru import logger

from bot.app import BotApp
from config.settings import Settings

async def main() -> None:
    """Главная функция запуска приложения."""
    try:
        settings = Settings()
        app = BotApp(settings)
        await app.run()
    except KeyboardInterrupt:
        logger.info("Приложение остановлено пользователем")
    except Exception as e:
        logger.error(f"Фатальная ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if sys.version_info < (3, 8):
        logger.error("Требуется Python 3.8 или выше")
        sys.exit(1)
    
    asyncio.run(main())
