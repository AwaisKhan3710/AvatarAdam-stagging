"""Dealership model with RAG metadata support."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.document import Document, DocumentChunk
    from app.models.user import User


class Dealership(Base):
    """Dealership model with RAG configuration."""

    __tablename__ = "dealerships"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, unique=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Contact information
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # RAG Configuration - stores vector DB metadata and settings
    # Multiple specialized knowledge bases organized by topic
    rag_config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # Example rag_config structure:
    # {
    #     "embedding_model": "text-embedding-3-small",
    #     "chunk_size": 1000,
    #     "chunk_overlap": 200,
    #     "collections": {
    #         "books": "dealership_123_books",
    #         "objection_handling": "dealership_123_objections",
    #         "playbooks": "dealership_123_playbooks",
    #         "videos": "dealership_123_videos",
    #         "compliance": "dealership_123_compliance",
    #         "product_knowledge": "dealership_123_products"
    #     },
    #     "metadata": {
    #         "dealership_id": 123,
    #         "dealership_name": "Premium Auto"
    #     }
    # }

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    users: Mapped[list["User"]] = relationship(
        "User", back_populates="dealership", cascade="all, delete-orphan"
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="dealership", cascade="all, delete-orphan"
    )
    document_chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="dealership", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Dealership(id={self.id}, name='{self.name}')>"
