"""Middleware для передачи зависимостей в обработчики."""

from .services import ServiceMiddleware

__all__ = [
    'ServiceMiddleware',
]
