"""Avatar API endpoints for HeyGen LiveAvatar integration."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from app.services.avatar_service import avatar_service


router = APIRouter()


class SessionTokenRequest(BaseModel):
    """Request body for creating a session token."""
    voice_id: Optional[str] = None


class SessionTokenResponse(BaseModel):
    """Response containing session token data."""
    session_id: str
    session_token: str


@router.post("/session", response_model=SessionTokenResponse)
async def create_avatar_session(request: SessionTokenRequest = SessionTokenRequest()):
    """
    Create a new HeyGen LiveAvatar session token.
    
    This endpoint creates a session token that the frontend uses to initialize
    the LiveAvatar SDK. The session uses FULL mode where HeyGen handles TTS -
    the frontend sends text and the avatar speaks it.
    
    Returns:
        SessionTokenResponse with session_id and session_token
    """
    try:
        result = await avatar_service.create_session_token(voice_id=request.voice_id)
        return SessionTokenResponse(
            session_id=result["session_id"],
            session_token=result["session_token"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create avatar session: {str(e)}",
        )


@router.get("/voices")
async def list_avatar_voices():
    """
    List available voices for the avatar.
    
    Returns:
        List of available voice configurations
    """
    try:
        voices = await avatar_service.list_voices()
        return {"voices": voices}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list voices: {str(e)}",
        )
