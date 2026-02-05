"""RAG (Retrieval-Augmented Generation) management endpoints."""

import io
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.middleware.rate_limit import limiter, UPLOAD_LIMIT
from app.models.dealership import Dealership
from app.models.user import User, UserRole
from app.schemas.common import MessageResponse
from app.services.rag_service import get_rag_service

logger = logging.getLogger(__name__)

router = APIRouter()

# Security: File upload limits
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB per file
MAX_TOTAL_SIZE = 50 * 1024 * 1024  # 50MB total per request
ALLOWED_EXTENSIONS = {".txt", ".pdf", ".docx"}
ALLOWED_MIME_TYPES = {
    "text/plain",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    # Some systems report these alternative MIME types
    "application/x-pdf",
    "application/octet-stream",  # Allow but verify extension
}


def _validate_file(file: UploadFile, content: bytes) -> None:
    """Validate uploaded file for security."""
    filename = file.filename or "unknown"
    filename_lower = filename.lower()

    # Check file extension
    ext = None
    for allowed_ext in ALLOWED_EXTENSIONS:
        if filename_lower.endswith(allowed_ext):
            ext = allowed_ext
            break

    if ext is None:
        raise ValidationError(
            f"File type not allowed: {filename}. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Check file size
    if len(content) > MAX_FILE_SIZE:
        raise ValidationError(
            f"File too large: {filename} ({len(content) / 1024 / 1024:.1f}MB). "
            f"Maximum size: {MAX_FILE_SIZE / 1024 / 1024:.0f}MB"
        )

    # Check MIME type (but don't rely solely on it as it can be spoofed)
    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        logger.warning(
            f"Unexpected MIME type '{file.content_type}' for file '{filename}', "
            f"but extension is valid. Proceeding with caution."
        )


def _extract_text_from_file(file_content: bytes, filename: str) -> str:
    """Extract text from uploaded file based on file type."""
    filename_lower = filename.lower()

    if filename_lower.endswith(".txt"):
        return file_content.decode("utf-8", errors="ignore")

    elif filename_lower.endswith(".pdf"):
        try:
            from pypdf import PdfReader

            pdf_reader = PdfReader(io.BytesIO(file_content))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception:
            # Don't expose internal error details
            logger.exception(f"Failed to parse PDF: {filename}")
            raise ValidationError(
                "Failed to read PDF file. Please ensure the file is not corrupted."
            )

    elif filename_lower.endswith(".docx"):
        try:
            from docx import Document

            doc = Document(io.BytesIO(file_content))
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except Exception:
            # Don't expose internal error details
            logger.exception(f"Failed to parse DOCX: {filename}")
            raise ValidationError(
                "Failed to read DOCX file. Please ensure the file is not corrupted."
            )

    else:
        raise ValidationError(
            f"Unsupported file type: {filename}. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )


@router.post(
    "/{dealership_id}/initialize",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def initialize_rag(
    dealership_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> MessageResponse:
    """
    Initialize RAG for a dealership.

    This creates:
    1. Pinecone namespace for the dealership
    2. Default RAG configuration
    3. Metadata structure for filtering

    Args:
        dealership_id: Dealership ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        Success message

    Raises:
        NotFoundError: If dealership not found
        AuthorizationError: If user is not dealership admin
    """
    # Get dealership
    result = await db.execute(select(Dealership).where(Dealership.id == dealership_id))
    dealership = result.scalar_one_or_none()

    if not dealership:
        raise NotFoundError("Dealership not found")

    # Check permissions
    if current_user.role == UserRole.SUPER_ADMIN:
        pass
    elif current_user.role == UserRole.DEALERSHIP_ADMIN:
        if current_user.dealership_id != dealership_id:
            raise AuthorizationError(
                "You can only initialize RAG for your own dealership"
            )
    else:
        raise AuthorizationError("Only dealership admins can initialize RAG")

    # Check if RAG already initialized
    if dealership.rag_config:
        raise ValidationError("RAG already initialized for this dealership")

    # Initialize RAG using service
    rag_service = get_rag_service()
    rag_config = await rag_service.initialize_namespace(
        dealership_id=dealership_id,
        dealership_name=dealership.name,
    )

    dealership.rag_config = rag_config
    db.add(dealership)
    await db.commit()

    return MessageResponse(
        message=f"RAG initialized for dealership '{dealership.name}'"
    )


@router.post(
    "/{dealership_id}/upload/{topic}",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(UPLOAD_LIMIT)
async def upload_documents(
    request: Request,
    dealership_id: int,
    topic: str,
    files: Annotated[list[UploadFile], File(...)],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> MessageResponse:
    """
    Upload documents to dealership's topic-specific RAG knowledge base.

    Topics: books, objection_handling, playbooks, videos, compliance, product_knowledge

    Supported file types: PDF, DOCX, TXT (max 10MB per file, 50MB total)

    Process:
    1. Validate dealership and permissions
    2. Validate file types and sizes
    3. Extract text from uploaded files
    4. Chunk documents and generate embeddings
    5. Store in Pinecone with topic metadata

    Args:
        request: FastAPI request object (required for rate limiting)
        dealership_id: Dealership ID
        topic: Topic category
        files: List of files to upload
        db: Database session
        current_user: Current authenticated user

    Returns:
        Success message with document count
    """
    # Get dealership
    result = await db.execute(select(Dealership).where(Dealership.id == dealership_id))
    dealership = result.scalar_one_or_none()

    if not dealership:
        raise NotFoundError("Dealership not found")

    # Check permissions
    if current_user.role == UserRole.SUPER_ADMIN:
        pass
    elif current_user.role == UserRole.DEALERSHIP_ADMIN:
        if current_user.dealership_id != dealership_id:
            raise AuthorizationError(
                "You can only upload documents to your own dealership"
            )
    else:
        raise AuthorizationError("Only dealership admins can upload documents")

    # Check if RAG is initialized
    if not dealership.rag_config:
        raise ValidationError("RAG not initialized. Please initialize RAG first.")

    rag_config = dealership.rag_config

    # Validate topic
    valid_topics = rag_config.get("topics", [])
    if topic not in valid_topics:
        raise ValidationError(
            f"Invalid topic '{topic}'. Valid topics: {', '.join(valid_topics)}"
        )

    # Security: Validate and extract text from files
    texts = []
    filenames = []
    total_size = 0

    for file in files:
        content = await file.read()
        total_size += len(content)

        # Check total upload size
        if total_size > MAX_TOTAL_SIZE:
            raise ValidationError(
                f"Total upload size exceeds limit ({MAX_TOTAL_SIZE / 1024 / 1024:.0f}MB). "
                "Please upload fewer files at once."
            )

        # Validate individual file
        _validate_file(file, content)

        # Extract text
        text = _extract_text_from_file(content, file.filename or "unknown.txt")
        if text.strip():
            texts.append(text)
            filenames.append(file.filename or "unknown")

    if not texts:
        raise ValidationError(
            "No valid text could be extracted from the uploaded files"
        )

    # Upload to Pinecone
    rag_service = get_rag_service()
    chunks_uploaded = await rag_service.upload_documents(
        texts=texts,
        dealership_id=dealership_id,
        topic=topic,
        filenames=filenames,
    )

    # Update document count for this topic
    if "document_counts" not in rag_config:
        rag_config["document_counts"] = {}
    rag_config["document_counts"][topic] = rag_config["document_counts"].get(
        topic, 0
    ) + len(files)
    dealership.rag_config = rag_config
    db.add(dealership)
    await db.commit()

    return MessageResponse(
        message=f"Successfully uploaded {len(files)} document(s) ({chunks_uploaded} chunks) to '{topic}' knowledge base"
    )


@router.get(
    "/{dealership_id}/status",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
)
async def get_rag_status(
    dealership_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> dict[str, Any]:
    """
    Get RAG status for a dealership.

    Args:
        dealership_id: Dealership ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        RAG configuration and status including vector counts
    """
    # Get dealership
    result = await db.execute(select(Dealership).where(Dealership.id == dealership_id))
    dealership = result.scalar_one_or_none()

    if not dealership:
        raise NotFoundError("Dealership not found")

    # Check access
    if current_user.role != UserRole.SUPER_ADMIN:
        if current_user.dealership_id != dealership_id:
            raise AuthorizationError("Access denied to this dealership")

    if not dealership.rag_config:
        return {
            "initialized": False,
            "message": "RAG not initialized for this dealership",
        }

    # Get actual stats from Pinecone
    rag_service = get_rag_service()
    stats = await rag_service.get_stats(dealership_id)

    return {
        "initialized": True,
        "dealership_id": dealership_id,
        "dealership_name": dealership.name,
        "config": dealership.rag_config,
        "total_documents": stats.get("total_documents", 0),
        "total_chunks": stats.get("total_chunks", 0),
        "documents_by_topic": stats.get("documents_by_topic", {}),
        "vector_db": stats.get("vector_db", "pinecone"),
        "pinecone_vector_count": stats.get("pinecone_vector_count", 0),
    }


@router.post(
    "/{dealership_id}/query",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
)
async def query_rag(
    dealership_id: int,
    query: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    topics: list[str] | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    """
    Query the RAG knowledge base.

    Args:
        dealership_id: Dealership ID
        query: Search query
        topics: Optional list of topics to filter by
        top_k: Number of results
        db: Database session
        current_user: Current authenticated user

    Returns:
        Retrieved documents with relevance scores
    """
    # Get dealership
    result = await db.execute(select(Dealership).where(Dealership.id == dealership_id))
    dealership = result.scalar_one_or_none()

    if not dealership:
        raise NotFoundError("Dealership not found")

    # Check access
    if current_user.role != UserRole.SUPER_ADMIN:
        if current_user.dealership_id != dealership_id:
            raise AuthorizationError("Access denied to this dealership")

    if not dealership.rag_config:
        raise ValidationError("RAG not initialized for this dealership")

    # Query Pinecone
    rag_service = get_rag_service()
    documents = await rag_service.query(
        query=query,
        dealership_id=dealership_id,
        topics=topics,
        top_k=top_k,
    )

    return {
        "query": query,
        "results": documents,
        "count": len(documents),
    }


@router.delete(
    "/{dealership_id}/reset",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def reset_rag(
    dealership_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> MessageResponse:
    """
    Reset RAG for a dealership (deletes all documents and config).

    Args:
        dealership_id: Dealership ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        Success message
    """
    # Get dealership
    result = await db.execute(select(Dealership).where(Dealership.id == dealership_id))
    dealership = result.scalar_one_or_none()

    if not dealership:
        raise NotFoundError("Dealership not found")

    # Only super admin or dealership admin can reset
    if current_user.role == UserRole.SUPER_ADMIN:
        pass
    elif current_user.role == UserRole.DEALERSHIP_ADMIN:
        if current_user.dealership_id != dealership_id:
            raise AuthorizationError("You can only reset RAG for your own dealership")
    else:
        raise AuthorizationError("Only admins can reset RAG")

    if not dealership.rag_config:
        raise ValidationError("RAG not initialized for this dealership")

    # Delete from Pinecone
    rag_service = get_rag_service()
    await rag_service.delete_namespace(dealership_id)

    # Clear RAG config
    dealership.rag_config = None
    db.add(dealership)
    await db.commit()

    return MessageResponse(message=f"RAG reset for dealership '{dealership.name}'")
