"""Common Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TimestampSchema(BaseSchema):
    """Schema with timestamp fields."""

    created_at: datetime
    updated_at: datetime


class ErrorResponse(BaseModel):
    """Standard error response schema."""

    error: dict[str, str | list[dict[str, str]]]


class MessageResponse(BaseModel):
    """Standard message response schema."""

    message: str
