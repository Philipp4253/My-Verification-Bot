"""
Модель для отслеживаемой группы.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Group(BaseModel):
    """
    Pydantic-модель для группы, соответствующая структуре в БД.
    """
    group_id: int
    group_name: str
    is_active: bool = True
    checkin_mode: bool = False
    added_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
