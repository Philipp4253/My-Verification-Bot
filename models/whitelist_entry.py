"""
Модель для записи в белом списке (whitelist).
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class WhitelistEntry(BaseModel):
    """
    Pydantic-модель для записи в whitelist, соответствующая структуре в БД.
    """
    id: Optional[int] = None
    group_id: int
    user_id: Optional[int] = None
    added_by: int
    added_at: Optional[datetime] = None
    notes: Optional[str] = None
    username: Optional[str] = None
    input_type: str = "id"
