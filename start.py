#!/usr/bin/env python3
"""
Простой запуск Telegram-бота верификации врачей.

Использование:
    python start.py
"""

import sys
import os
from pathlib import Path
import asyncio
import platform

# Импортируем traceback для детального вывода ошибок
import traceback

from loguru import logger

from bot.app import BotApp
from config.settings import settings

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def main():
    """Основная функция для запуска бота."""
    try:
        # Настройка логирования
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
        logger.add("bot.log", level="DEBUG", rotation="10 MB", retention=1)

        env_file = project_root / ".env"
        if not env_file.exists():
            print("❌ Ошибка: файл .env не найден!")
            print("💡 Создайте файл .env на основе env.example")
            print("📋 Пример команды: cp env.example .env")
            sys.exit(1)

        if sys.version_info < (3, 8):
            print("❌ Ошибка: требуется Python 3.8 или выше")
            print(f"📋 Текущая версия: {sys.version}")
            sys.exit(1)

        logger.info("🚀 Запуск бота верификации врачей...")
        logger.info("📋 Для остановки нажмите Ctrl+C")

        # Настройки уже загружены при импорте
        # Создание и запуск приложения
        app = BotApp(settings)
        asyncio.run(app.run())

    except ImportError as e:
        logger.critical(f"❌ Ошибка импорта: {e}")
        # Печатаем полный traceback, чтобы увидеть, где именно проблема
        traceback.print_exc()
        logger.info("💡 Установите зависимости: pip install -r requirements.txt")
    except (KeyboardInterrupt, SystemExit):
        logger.info("✅ Бот остановлен.")
    except Exception as e:
        logger.critical(f"💥 Непредвиденная ошибка: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    # Проверка версии Python
    logger.info(f"Запуск на Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    if sys.version_info < (3, 12):
        logger.critical("Требуется Python 3.12 или выше.")
    else:
        main()
