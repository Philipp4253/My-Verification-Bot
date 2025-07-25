"""
Модуль управления whitelist.

Объединяет все роутеры для работы с белым списком пользователей.
"""
from aiogram import Router

from .handlers import router as handlers_router
from .add_user import router as add_user_router
from .remove_user import router as remove_user_router

whitelist_router = Router()
whitelist_router.include_router(add_user_router)
whitelist_router.include_router(remove_user_router)
whitelist_router.include_router(handlers_router)
