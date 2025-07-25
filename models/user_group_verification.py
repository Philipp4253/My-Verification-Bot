"""Модель для верификации пользователей в группах."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class UserGroupVerification(BaseModel):
    """Модель для хранения статуса верификации пользователя в конкретной группе."""

    id: Optional[int] = None
    user_id: int
    group_id: int
    verified: bool = False
    requires_verification: bool = False  # True только для тех, кого видели присоединяющимися
    verification_type: Optional[str] = None  # "manual", "auto_verified", etc.
    verified_at: Optional[datetime] = None
    attempts_count: int = 0
    state: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
