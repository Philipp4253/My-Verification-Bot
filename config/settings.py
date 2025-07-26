"""Настройки конфигурации для бота верификации врачей."""
from typing import List, Optional, Any
from pydantic import Field, field_validator, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseSettings

class Settings(BaseSettings):
    # ID групп для модерации (добавьте свои реальные ID через запятую)
    MODERATED_CHATS: list[int] = [-10012345678]  # Пример ID группы (замените на реальный)
    
    # ID администраторов бота (ваш личный ID)
    ADMIN_USER_IDS: list[int] = [123456789]  # Ваш Telegram ID
    
    # Время на верификацию (в часах)
    VERIFICATION_TIME_LIMIT: int = 24  # 24 часа
    
    # Интервал проверки (в секундах)
    CHECK_INTERVAL: int = 60  # Для теста: 60 сек = 1 минута (в продакшене 3600 = 1 час)
    
    # Настройки базы данных
    DATABASE_URL: str = "sqlite:///database.db"
    
    # Токен бота (лучше через .env)
    BOT_TOKEN: str = "ваш_токен_бота"

    class Config:
        env_file = ".env"  # Для загрузки настроек из .env файла

settings = Settings()


class Settings(BaseSettings):
    """Настройки приложения с валидацией."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    telegram_bot_token: SecretStr = Field(..., description="Токен Telegram бота")
    telegram_group_id: Optional[int] = Field(None, description="ID основной группы (необязательно)")

    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    openai_model: str = Field("gpt-4o", alias="OPENAI_MODEL")

    database_path: str = "./sqlite.db"

    max_file_size_mb: int = 20
    allowed_file_types: str = "image/jpeg,image/png,application/pdf"

    auto_delete_unverified: bool = Field(True, alias="AUTO_DELETE_UNVERIFIED")

    enable_spam_protection: bool = Field(False, alias="ENABLE_SPAM_PROTECTION")

    auto_delete_logs_days: int = 30

    max_verification_attempts: int = 3

    verification_start_timeout_hours: int = Field(12, description="Время на начало верификации в часах")
    verification_complete_timeout_hours: int = Field(24, description="Время на завершение верификации в часах")

    admin_user_ids_str: Optional[str] = Field(None, alias="ADMIN_USER_IDS", description="Строка с ID администраторов")

    @property
    def admin_user_ids(self) -> List[int]:
        """Возвращает список ID администраторов."""
        if not self.admin_user_ids_str or not self.admin_user_ids_str.strip():
            return []

        try:
            return [int(i.strip()) for i in self.admin_user_ids_str.split(",") if i.strip()]
        except ValueError:
            raise ValueError("ADMIN_USER_IDS должен быть списком чисел, разделенных запятыми")

    def get_telegram_bot_token(self) -> str:
        """Возвращает токен бота в виде строки."""
        return self.telegram_bot_token.get_secret_value()

    def get_allowed_file_types(self) -> List[str]:
        """Возвращает список разрешенных типов файлов."""
        if self.allowed_file_types:
            return [ft.strip() for ft in self.allowed_file_types.split(',') if ft.strip()]
        return []

    @property
    def max_file_size_bytes(self) -> int:
        """Преобразует размер файла из МБ в байты."""
        return self.max_file_size_mb * 1024 * 1024

    def format_verification_start_timeout(self) -> str:
        """Форматирует время на начало верификации с правильным склонением."""
        hours = self.verification_start_timeout_hours
        if hours >= 24 and hours % 24 == 0:
            days = hours // 24
            if days == 1:
                return "1 день"
            elif 2 <= days <= 4:
                return f"{days} дня"
            else:
                return f"{days} дней"
        elif hours < 1:
            minutes = int(hours * 60)
            if minutes == 1:
                return "1 минуту"
            elif 2 <= minutes <= 4:
                return f"{minutes} минуты"
            else:
                return f"{minutes} минут"
        else:
            if hours == 1:
                return "1 час"
            elif 2 <= hours <= 4:
                return f"{hours} часа"
            else:
                return f"{hours} часов"

    def format_verification_complete_timeout(self) -> str:
        """Форматирует время на завершение верификации с правильным склонением."""
        hours = self.verification_complete_timeout_hours
        if hours >= 24 and hours % 24 == 0:
            days = hours // 24
            if days == 1:
                return "1 день"
            elif 2 <= days <= 4:
                return f"{days} дня"
            else:
                return f"{days} дней"
        else:
            if hours == 1:
                return "1 час"
            elif 2 <= hours <= 4:
                return f"{hours} часа"
            else:
                return f"{hours} часов"


settings = Settings()
