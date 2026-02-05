"""Dealership schemas."""

from typing import Any

from pydantic import Field

from app.schemas.common import BaseSchema, TimestampSchema


class DealershipBase(BaseSchema):
    """Base dealership schema."""

    name: str = Field(..., min_length=1, max_length=255)
    address: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None


class DealershipCreate(DealershipBase):
    """Dealership creation schema."""

    pass


class DealershipUpdate(BaseSchema):
    """Dealership update schema."""

    name: str | None = Field(None, min_length=1, max_length=255)
    is_active: bool | None = None
    address: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    rag_config: dict[str, Any] | None = None


class DealershipResponse(DealershipBase, TimestampSchema):
    """Dealership response schema."""

    id: int
    is_active: bool
    rag_config: dict[str, Any] | None


class RAGConfigUpdate(BaseSchema):
    """RAG configuration update schema."""

    vector_db_collection: str | None = None
    embedding_model: str | None = None
    chunk_size: int | None = Field(None, ge=100, le=5000)
    chunk_overlap: int | None = Field(None, ge=0, le=1000)
    metadata: dict[str, Any] | None = None
