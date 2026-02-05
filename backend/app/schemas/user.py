"""User schemas."""

import re
from datetime import datetime

from pydantic import EmailStr, Field, field_validator

from app.models.user import UserRole
from app.schemas.common import BaseSchema, TimestampSchema


class UserBase(BaseSchema):
    """Base user schema."""

    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)


class UserCreate(UserBase):
    """User creation schema."""

    password: str = Field(..., min_length=8, max_length=100)
    role: UserRole = UserRole.USER
    dealership_id: int | None = None

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        """
        Validate password complexity requirements.

        Password must contain:
        - At least 8 characters (enforced by Field)
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character
        """
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]\\;'/`~]", v):
            raise ValueError("Password must contain at least one special character")
        return v


class UserUpdate(BaseSchema):
    """User update schema."""

    email: EmailStr | None = None
    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    is_active: bool | None = None
    role: UserRole | None = None


class UserResponse(UserBase, TimestampSchema):
    """User response schema."""

    id: int
    role: UserRole
    is_active: bool
    is_verified: bool
    dealership_id: int | None
    last_login: datetime | None

    @property
    def full_name(self) -> str:
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}"


class UserInDB(UserResponse):
    """User schema with hashed password (internal use only)."""

    hashed_password: str
