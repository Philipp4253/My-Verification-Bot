from aiogram import Router

from .handlers import admin_handlers_router
from .whitelist import whitelist_router
from .checkin import checkin_router

admin_router = Router(name="admin_main")
admin_router.include_router(admin_handlers_router)
admin_router.include_router(whitelist_router)
admin_router.include_router(checkin_router)
