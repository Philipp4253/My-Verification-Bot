from datetime import datetime
from typing import Optional

from aiogram.types import User as AiogramUser
from pydantic import BaseModel


class User(BaseModel):
    """
    Pydantic-модель для пользователя, соответствующая структуре в БД.
    """

    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: Optional[str] = None
    is_premium: Optional[bool] = False
    verified: Optional[bool] = False
    verified_at: Optional[datetime] = None
    state: Optional[str] = None
    created_at: Optional[datetime] = None
    attempts_count: Optional[int] = 0

    @classmethod
    def from_aiogram(cls, user: AiogramUser) -> "User":
        """
        Создает экземпляр User из объекта пользователя aiogram.
        """
        return cls(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            language_code=user.language_code,
            is_premium=user.is_premium,
        )
