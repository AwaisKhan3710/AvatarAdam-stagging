"""Dependency injection for API endpoints."""

from typing import Annotated

from fastapi import Depends, WebSocket, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, async_session_maker
from app.core.exceptions import AuthenticationError
from app.core.security import decode_token, verify_token_type
from app.models.user import User

# Security scheme for JWT Bearer tokens
security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer credentials
        db: Database session

    Returns:
        User: Current authenticated user

    Raises:
        AuthenticationError: If token is invalid or user not found
    """
    token = credentials.credentials

    # Decode and verify token
    payload = decode_token(token)
    verify_token_type(payload, "access")

    # Extract user ID
    user_id = payload.get("sub")
    if user_id is None:
        raise AuthenticationError("Token missing user identifier")

    # Get user from database
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise AuthenticationError("User not found")

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Get current active user.

    Args:
        current_user: Current authenticated user

    Returns:
        User: Current active user

    Raises:
        AuthenticationError: If user is not active
    """
    if not current_user.is_active:
        raise AuthenticationError("User account is inactive")

    return current_user


async def authenticate_websocket(websocket: WebSocket) -> User | None:
    """
    Authenticate a WebSocket connection using JWT token.

    Token can be provided via:
    1. Query parameter: ?token=<jwt_token>
    2. First message after connection: {"type": "auth", "token": "<jwt_token>"}

    Args:
        websocket: WebSocket connection

    Returns:
        User if authenticated, None otherwise
    """
    # Try to get token from query params first
    token = websocket.query_params.get("token")

    if not token:
        return None

    try:
        # Decode and verify token
        payload = decode_token(token)
        verify_token_type(payload, "access")

        # Extract user ID
        user_id = payload.get("sub")
        if user_id is None:
            return None

        # Get user from database
        async with async_session_maker() as db:
            result = await db.execute(select(User).where(User.id == int(user_id)))
            user = result.scalar_one_or_none()

            if user is None or not user.is_active:
                return None

            return user
    except Exception:
        return None


async def require_websocket_auth(websocket: WebSocket, expected_user_id: int) -> User:
    """
    Require authentication for WebSocket and verify user ID matches.

    Args:
        websocket: WebSocket connection
        expected_user_id: The user_id from the URL path

    Returns:
        Authenticated User

    Raises:
        Closes WebSocket with 4001 (Unauthorized) or 4003 (Forbidden)
    """
    user = await authenticate_websocket(websocket)

    if user is None:
        await websocket.close(code=4001, reason="Authentication required")
        raise AuthenticationError("WebSocket authentication failed")

    # Verify the user_id in the URL matches the authenticated user
    if user.id != expected_user_id:
        await websocket.close(code=4003, reason="User ID mismatch")
        raise AuthenticationError("User ID does not match authenticated user")

    return user
