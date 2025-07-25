"""
Модель администратора.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Admin(BaseModel):
    """
    Pydantic-модель для администратора, соответствующая структуре в БД.
    """
    id: Optional[int] = None
    user_id: int
    group_id: Optional[int] = None
    role: str = "administrator"
    added_at: Optional[datetime] = None
