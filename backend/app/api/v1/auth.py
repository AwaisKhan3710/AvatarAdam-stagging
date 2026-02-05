"""Authentication endpoints - Login and Signup only."""

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    get_token_hash,
    verify_password,
    verify_token_type,
)
from app.middleware.rate_limit import limiter, AUTH_LIMIT
from app.models.refresh_token import RefreshToken
from app.models.user import User, UserRole
from app.schemas.auth import LoginRequest, RefreshTokenRequest, TokenResponse
from app.schemas.user import UserCreate, UserResponse

router = APIRouter()


@router.post(
    "/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit(AUTH_LIMIT)
async def signup(
    request: Request,
    user_data: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """
    Register a new user and return JWT tokens.

    Args:
        request: FastAPI request object (required for rate limiting)
        user_data: User registration data
        db: Database session

    Returns:
        TokenResponse: Access and refresh tokens

    Raises:
        ConflictError: If user with email already exists
    """
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise ConflictError("User with this email already exists")

    # Security: Restrict signup to regular users only
    # Admins must be created by existing super_admin
    if user_data.role != UserRole.USER:
        raise ConflictError(
            "Self-registration is only allowed for regular users. Contact an admin for elevated privileges."
        )

    # Create new user
    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        role=user_data.role,
        dealership_id=user_data.dealership_id,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    # Create tokens with user claims
    additional_claims = {
        "email": user.email,
        "role": user.role.value,
        "dealership_id": user.dealership_id,
    }

    access_token = create_access_token(
        subject=user.id, additional_claims=additional_claims
    )
    refresh_token = create_refresh_token(
        subject=user.id, additional_claims=additional_claims
    )

    # Store refresh token in database
    token_hash = get_token_hash(refresh_token)
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    user_agent = request.headers.get("user-agent")
    client_host = request.client.host if request.client else None

    db_token = RefreshToken(
        token_hash=token_hash,
        user_id=user.id,
        expires_at=expires_at,
        user_agent=user_agent,
        ip_address=client_host,
    )
    db.add(db_token)
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
@limiter.limit(AUTH_LIMIT)
async def login(
    request: Request,
    credentials: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """
    Authenticate user and return JWT tokens.

    Args:
        request: FastAPI request object (required for rate limiting)
        credentials: Login credentials (email and password)
        db: Database session

    Returns:
        TokenResponse: Access and refresh tokens

    Raises:
        AuthenticationError: If credentials are invalid
    """
    # Get user by email
    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalar_one_or_none()

    # Verify user exists and password is correct
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise AuthenticationError("Incorrect email or password")

    if not user.is_active:
        raise AuthenticationError("User account is inactive")

    # Create tokens with user claims
    additional_claims = {
        "email": user.email,
        "role": user.role.value,
        "dealership_id": user.dealership_id,
    }

    access_token = create_access_token(
        subject=user.id, additional_claims=additional_claims
    )
    refresh_token = create_refresh_token(
        subject=user.id, additional_claims=additional_claims
    )

    # Store refresh token in database
    token_hash = get_token_hash(refresh_token)
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    user_agent = request.headers.get("user-agent")
    client_host = request.client.host if request.client else None

    db_token = RefreshToken(
        token_hash=token_hash,
        user_id=user.id,
        expires_at=expires_at,
        user_agent=user_agent,
        ip_address=client_host,
    )
    db.add(db_token)

    # Update last login timestamp
    user.last_login = datetime.now(timezone.utc)
    db.add(user)

    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh_token(
    token_request: RefreshTokenRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """
    Refresh access token using refresh token.

    Args:
        token_request: Request body containing refresh token
        request: FastAPI request object
        db: Database session

    Returns:
        TokenResponse: New access and refresh tokens

    Raises:
        AuthenticationError: If refresh token is invalid or expired
    """
    refresh_token_str = token_request.refresh_token

    # Decode and verify refresh token
    try:
        payload = decode_token(refresh_token_str)
        verify_token_type(payload, "refresh")
    except Exception:
        raise AuthenticationError("Invalid refresh token")

    # Check if token exists and is valid in database
    token_hash = get_token_hash(refresh_token_str)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    db_token = result.scalar_one_or_none()

    if not db_token or db_token.revoked or db_token.is_expired:
        raise AuthenticationError("Refresh token is invalid or expired")

    # Get user
    user_id = payload.get("sub")
    if user_id is None:
        raise AuthenticationError("Invalid token: missing user ID")
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise AuthenticationError("User not found or inactive")

    # Create new tokens
    additional_claims = {
        "email": user.email,
        "role": user.role.value,
        "dealership_id": user.dealership_id,
    }

    new_access_token = create_access_token(
        subject=user.id, additional_claims=additional_claims
    )
    new_refresh_token = create_refresh_token(
        subject=user.id, additional_claims=additional_claims
    )

    # Revoke old refresh token
    db_token.revoked = True
    db_token.revoked_at = datetime.now(timezone.utc)
    db.add(db_token)

    # Store new refresh token
    new_token_hash = get_token_hash(new_refresh_token)
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    user_agent = request.headers.get("user-agent")
    client_host = request.client.host if request.client else None

    new_db_token = RefreshToken(
        token_hash=new_token_hash,
        user_id=user.id,
        expires_at=expires_at,
        user_agent=user_agent,
        ip_address=client_host,
    )
    db.add(new_db_token)
    await db.commit()

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UserResponse:
    """
    Get current authenticated user information.

    Args:
        current_user: Current authenticated user

    Returns:
        UserResponse: Current user information
    """
    return UserResponse.model_validate(current_user)
