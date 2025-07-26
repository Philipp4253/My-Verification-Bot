"""Настройки конфигурации для бота верификации врачей."""
from typing import List, Optional
from pydantic import Field, field_validator, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Основные настройки приложения."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # 1. Настройки Telegram
    BOT_TOKEN: SecretStr = Field(..., description="Токен Telegram бота")
    MODERATED_CHATS: List[int] = Field(
        default=[-10012345678],
        description="ID групп для модерации (через запятую в .env)"
    )
    ADMIN_USER_IDS: List[int] = Field(
        default=[123456789],
        description="ID администраторов бота"
    )

    # 2. Настройки верификации
    VERIFICATION_TIME_LIMIT: int = Field(
        default=24,
        description="Время на верификацию в часах"
    )
    CHECK_INTERVAL: int = Field(
        default=3600,
        description="Интервал проверки в секундах (3600 = 1 час)"
    )
    MAX_VERIFICATION_ATTEMPTS: int = Field(
        default=3,
        description="Максимальное количество попыток верификации"
    )

    # 3. Настройки базы данных
    DATABASE_URL: str = Field(
        default="sqlite:///database.db",
        description="URL подключения к БД"
    )

    # 4. Настройки файлов
    MAX_FILE_SIZE_MB: int = Field(
        default=20,
        description="Максимальный размер файла (МБ)"
    )
    ALLOWED_FILE_TYPES: str = Field(
        default="image/jpeg,image/png,application/pdf",
        description="Разрешенные типы файлов (через запятую)"
    )

    # 5. Флаги функционала
    AUTO_DELETE_UNVERIFIED: bool = Field(
        default=True,
        description="Автоматически удалять неверифицированных"
    )
    ENABLE_SPAM_PROTECTION: bool = Field(
        default=False,
        description="Включить защиту от спама"
    )

    # Валидаторы
    @field_validator('MODERATED_CHATS', 'ADMIN_USER_IDS', mode='before')
    def parse_ids(cls, value):
        if isinstance(value, str):
            return [int(x.strip()) for x in value.split(',')]
        return value

    @field_validator('ALLOWED_FILE_TYPES')
    def parse_file_types(cls, value):
        return [x.strip() for x in value.split(',')]

    # Методы для удобства
    def get_bot_token(self) -> str:
        """Получить токен бота в виде строки."""
        return self.BOT_TOKEN.get_secret_value()

    @property
    def max_file_size_bytes(self) -> int:
        """Максимальный размер файла в байтах."""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    def format_timeout(self, hours: int) -> str:
        """Форматирование времени с правильным склонением."""
        if hours >= 24 and hours % 24 == 0:
            days = hours // 24
            return f"{days} {_plural_days(days)}"
        return f"{hours} {_plural_hours(hours)}"

def _plural_days(n: int) -> str:
    """Склонение для дней."""
    if n % 10 == 1 and n % 100 != 11:
        return "день"
    if 2 <= n % 10 <= 4 and (n % 100 < 10 or n % 100 >= 20):
        return "дня"
    return "дней"

def _plural_hours(n: int) -> str:
    """Склонение для часов."""
    if n % 10 == 1 and n % 100 != 11:
        return "час"
    if 2 <= n % 10 <= 4 and (n % 100 < 10 or n % 100 >= 20):
        return "часа"
    return "часов"


# Инициализация настроек
settings = Settings()
