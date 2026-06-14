from fastapi import APIRouter

from app.api.v1 import admin, auth, calendar, chat, email, memory

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(chat.router)
api_router.include_router(email.router)
api_router.include_router(calendar.router)
api_router.include_router(memory.router)
api_router.include_router(admin.router)
