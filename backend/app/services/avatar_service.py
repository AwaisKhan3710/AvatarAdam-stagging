"""HeyGen LiveAvatar service for interactive avatar sessions."""

import httpx
from typing import Optional

from app.core.config import settings


class AvatarService:
    """Service for managing HeyGen LiveAvatar sessions."""

    def __init__(self):
        self.api_url = settings.HEYGEN_API_URL
        self.api_key = settings.HEYGEN_API_KEY
        self.avatar_id = settings.HEYGEN_AVATAR_ID
        self.sandbox_mode = settings.HEYGEN_SANDBOX_MODE

    async def create_session_token(self, voice_id: Optional[str] = None) -> dict:
        """
        Create a new LiveAvatar session token.
        
        Uses FULL mode for avatar capabilities, but we use repeat() method
        to make avatar speak our LLM responses (not HeyGen's AI).
        
        Args:
            voice_id: Optional voice ID to use. If not provided, uses avatar's default voice.
            
        Returns:
            dict with session_id and session_token
        """
        payload = {
            "mode": "FULL",  # FULL mode for avatar, but we use repeat() not message()
            "avatar_id": self.avatar_id,
            "is_sandbox": self.sandbox_mode,
            "avatar_persona": {},  # Required for FULL mode
        }
        
        # Add voice configuration if specified
        if voice_id:
            payload["avatar_persona"]["voice_id"] = voice_id

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.api_url}/v1/sessions/token",
                headers={
                    "X-API-KEY": self.api_key,
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", data)

    async def list_voices(self) -> list:
        """
        List available voices for the avatar.
        
        Returns:
            List of available voice configurations
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.api_url}/v1/voices",
                headers={
                    "X-API-KEY": self.api_key,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", data)


# Singleton instance
avatar_service = AvatarService()
