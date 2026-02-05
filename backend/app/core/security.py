"""Security utilities for JWT tokens and password hashing."""

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings
from app.core.exceptions import AuthenticationError


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password from database

    Returns:
        bool: True if password matches, False otherwise
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        str: Hashed password
    """
    salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def create_access_token(
    subject: int | str,
    expires_delta: timedelta | None = None,
    additional_claims: dict[str, Any] | None = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        subject: User ID or identifier
        expires_delta: Token expiration time delta
        additional_claims: Additional claims to include in token

    Returns:
        str: Encoded JWT token
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "access",
    }

    if additional_claims:
        to_encode.update(additional_claims)

    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(
    subject: int | str,
    expires_delta: timedelta | None = None,
    additional_claims: dict[str, Any] | None = None,
) -> str:
    """
    Create a JWT refresh token.

    Args:
        subject: User ID or identifier
        expires_delta: Token expiration time delta
        additional_claims: Additional claims to include in token

    Returns:
        str: Encoded JWT token
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "refresh",
    }

    if additional_claims:
        to_encode.update(additional_claims)

    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and verify a JWT token.

    Args:
        token: JWT token string

    Returns:
        dict: Decoded token payload

    Raises:
        AuthenticationError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError as e:
        raise AuthenticationError(f"Invalid token: {str(e)}") from e


def verify_token_type(payload: dict[str, Any], expected_type: str) -> None:
    """
    Verify that token is of expected type.

    Args:
        payload: Decoded token payload
        expected_type: Expected token type ('access' or 'refresh')

    Raises:
        AuthenticationError: If token type doesn't match
    """
    token_type = payload.get("type")
    if token_type != expected_type:
        raise AuthenticationError(
            f"Invalid token type. Expected '{expected_type}', got '{token_type}'"
        )


def get_token_hash(token: str) -> str:
    """
    Create a hash of a token for storage.

    Args:
        token: JWT token string

    Returns:
        str: SHA-256 hash of the token
    """
    return hashlib.sha256(token.encode()).hexdigest()


def extract_user_id_from_token(token: str) -> int:
    """
    Extract user ID from JWT token.

    Args:
        token: JWT token string

    Returns:
        int: User ID

    Raises:
        AuthenticationError: If token is invalid or user ID is missing
    """
    payload = decode_token(token)
    user_id = payload.get("sub")

    if user_id is None:
        raise AuthenticationError("Token missing user identifier")

    try:
        return int(user_id)
    except ValueError as e:
        raise AuthenticationError("Invalid user identifier in token") from e
