from typing import List
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения с валидацией."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Telegram
    telegram_bot_token: SecretStr = Field(..., alias="TELEGRAM_BOT_TOKEN")
    telegram_group_id: int = Field(..., alias="TELEGRAM_GROUP_ID")
    admin_user_ids: List[int] = Field(..., alias="ADMIN_USER_IDS")

    # Верификация
    verification_start_timeout_hours: int = Field(..., alias="VERIFICATION_START_TIMEOUT_HOURS")
    verification_complete_timeout_hours: int = Field(..., alias="VERIFICATION_COMPLETE_TIMEOUT_HOURS")
    check_interval_seconds: int = Field(3600, alias="CHECK_INTERVAL_SECONDS")
    max_verification_attempts: int = Field(..., alias="MAX_VERIFICATION_ATTEMPTS")

    # База данных
    database_url: str = Field(..., alias="DATABASE_URL")

    # Файлы
    max_file_size_mb: int = Field(..., alias="MAX_FILE_SIZE_MB")
    allowed_file_types: List[str] = Field(..., alias="ALLOWED_FILE_TYPES")

    # Флаги
    auto_delete_unverified: bool = Field(..., alias="AUTO_DELETE_UNVERIFIED")
    enable_spam_protection: bool = Field(..., alias="ENABLE_SPAM_PROTECTION")
    auto_delete_logs_days: int = Field(..., alias="AUTO_DELETE_LOGS_DAYS")

    # OpenAI
    openai_api_key: str = Field(None, alias="OPENAI_API_KEY")
    openai_model: str = Field("gpt-4o", alias="OPENAI_MODEL")

    @field_validator('admin_user_ids', mode='before')
    def parse_admin_ids(cls, v):
        if isinstance(v, str):
            return [int(i.strip()) for i in v.split(',') if i.strip()]
        return v

     @field_validator('allowed_file_types', mode='before')
def parse_file_types(cls, v):
    if v is None:
        return ["image/jpeg", "image/png", "application/pdf"]
    if isinstance(v, str):
        return [ft.strip() for ft in v.split(',') if ft.strip()]
    return v

    def get_telegram_bot_token(self) -> str:
        return self.telegram_bot_token.get_secret_value()

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def moderated_chats(self) -> List[int]:
        return [self.telegram_group_id]


settings = Settings()
