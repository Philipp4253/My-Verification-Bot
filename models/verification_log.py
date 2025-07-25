"""
Модели, связанные с процессом верификации.
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class VerificationMethod(str, Enum):
    """Метод, используемый для верификации."""
    WEBSITE = "website"
    DOCUMENT = "document"


class VerificationStatus(str, Enum):
    """Статус верификации пользователя."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    VERIFIED = "verified"
    FAILED = "failed"
    TIMEOUT = "timeout"


class VerificationLog(BaseModel):
    """
    Pydantic-модель для лога верификации, соответствующая структуре в БД.
    """
    id: Optional[int] = None
    user_id: int
    method: Optional[VerificationMethod] = None
    full_name: Optional[str] = None
    workplace: Optional[str] = None
    website_url: Optional[str] = None
    details: Optional[str] = None
    openai_response: Optional[str] = None
    result: Optional[str] = None
    created_at: Optional[datetime] = None
