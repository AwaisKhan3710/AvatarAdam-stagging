"""API v1 routes."""

from fastapi import APIRouter

from app.api.v1 import auth, avatar, chat, dealerships, rag, report, users, voice, voice_live, voice_vad

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(
    dealerships.router, prefix="/dealerships", tags=["dealerships"]
)
api_router.include_router(rag.router, prefix="/rag", tags=["rag"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(voice.router, prefix="/voice", tags=["voice"])
# New production-ready live voice endpoint
api_router.include_router(voice_live.router, prefix="/voice", tags=["voice"])
# Voice Activity Detection endpoint
api_router.include_router(voice_vad.router, prefix="/voice", tags=["voice"])
# Report inaccuracy endpoint
api_router.include_router(report.router, prefix="/report", tags=["report"])
# HeyGen LiveAvatar endpoint
api_router.include_router(avatar.router, prefix="/avatar", tags=["avatar"])

__all__ = ["api_router"]
