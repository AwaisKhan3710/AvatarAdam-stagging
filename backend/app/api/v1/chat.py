"""Chat endpoints for conversational training and role-play."""

import enum
import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.middleware.rate_limit import limiter, CHAT_LIMIT
from app.models.dealership import Dealership
from app.models.user import User, UserRole
from app.services.llm_service import get_llm_service
from app.services.rag_service import get_rag_service

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatMode(str, enum.Enum):
    """Chat mode enumeration."""

    TRAINING = "training"  # AI acts as Adam (trainer)
    ROLEPLAY = "roleplay"  # AI acts as customer


class ChatMessage(BaseModel):
    """Chat message request schema."""

    message: str = Field(
        ..., min_length=1, max_length=5000, description="User's question or message"
    )
    mode: ChatMode = Field(
        default=ChatMode.TRAINING, description="Chat mode: training or roleplay"
    )
    session_id: str | None = Field(
        None, description="Optional session ID for conversation context"
    )
    conversation_history: list[dict] | None = Field(
        None, description="Previous messages for context"
    )
    dealership_id: int | None = Field(
        None,
        description="Dealership ID (required for super admin, optional for others)",
    )


class ChatResponse(BaseModel):
    """Chat response schema."""

    response: str = Field(..., description="AI-generated response")
    session_id: str = Field(..., description="Session ID for maintaining context")
    sources: list[dict[str, str]] | None = Field(
        None, description="Source documents used"
    )
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


@router.post("/", response_model=ChatResponse, status_code=status.HTTP_200_OK)
@limiter.limit(CHAT_LIMIT)
async def chat(
    request: Request,
    chat_message: ChatMessage,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> ChatResponse:
    """
    Chat with AI in either training or role-play mode.

    **Training Mode** (mode="training"):
    - AI acts as Adam Marburger (the trainer)
    - Answers questions based on dealership's RAG knowledge base
    - Provides teaching, guidance, and expertise

    **Role-Play Mode** (mode="roleplay"):
    - AI acts as a customer
    - Presents realistic objections and concerns
    - Helps users practice F&I scenarios

    Args:
        request: FastAPI request object (required for rate limiting)
        chat_message: User's message with mode selection
        db: Database session
        current_user: Current authenticated user

    Returns:
        AI-generated response with sources
    """
    # Determine dealership ID based on user role
    if current_user.role == UserRole.SUPER_ADMIN:
        # Super admin must provide dealership_id
        if not chat_message.dealership_id:
            raise ValidationError("Super admin must specify dealership_id")
        dealership_id = chat_message.dealership_id
    else:
        # Regular users use their assigned dealership
        if not current_user.dealership_id:
            raise ValidationError(
                "User must be associated with a dealership to use chat"
            )
        dealership_id = current_user.dealership_id

        # If dealership_id is provided, ensure it matches user's dealership
        if chat_message.dealership_id and chat_message.dealership_id != dealership_id:
            raise AuthorizationError(
                "You can only chat in the context of your own dealership"
            )

    # Get dealership and RAG config
    result = await db.execute(select(Dealership).where(Dealership.id == dealership_id))
    dealership = result.scalar_one_or_none()

    if not dealership:
        raise NotFoundError("Dealership not found")

    # Get services
    llm_service = get_llm_service()
    rag_service = get_rag_service()

    context = ""
    context_docs = []

    # Query RAG for context (both modes can use RAG if available)
    # OPTIMIZED: Removed topic classification LLM call - use direct semantic search
    # Pinecone's semantic search already finds the most relevant content across all topics
    logger.info(f"Chat - dealership.rag_config: {dealership.rag_config}")
    if dealership.rag_config:
        try:
            # Direct semantic search across all topics - no classification needed
            # The semantic similarity search will naturally return the most relevant content
            # This saves ~300-500ms by removing the topic classification LLM call
            #
            # Multi-level caching provides further optimization:
            # 1. Session context (pre-warmed): ~5-20ms
            # 2. Semantic cache (similar queries): ~10-50ms
            # 3. Embedding cache (same query): saves embedding computation
            # 4. Pinecone query (cache miss): ~200-400ms
            context_docs = await rag_service.query(
                query=chat_message.message,
                dealership_id=dealership.id,
                topics=None,  # Search all topics, let semantic similarity rank them
                top_k=5,
                session_id=chat_message.session_id,  # Use pre-warmed session context if available
            )
            logger.info(
                f"Chat - context_docs count (semantic search): {len(context_docs)}"
            )

            if context_docs:
                logger.info(
                    f"Chat - first doc preview: {context_docs[0].get('content', '')[:100]}..."
                )

            # Build context string with rich metadata
            if context_docs:
                context_parts = []
                for doc in context_docs:
                    topic = doc.get("topic", "unknown")
                    filename = doc.get("filename", "")
                    content = doc.get("content", "")
                    score = doc.get("score", 0)
                    context_parts.append(
                        f"[Source: {topic} | File: {filename} | Relevance: {score:.2f}]\n{content}"
                    )
                context = "\n\n---\n\n".join(context_parts)
                logger.info(f"Chat - context built, length: {len(context)}")
        except Exception as e:
            # If RAG query fails, continue without context
            logger.error(f"Chat - RAG query failed: {e}", exc_info=True)
            context = ""
            context_docs = []
    elif chat_message.mode == ChatMode.TRAINING:
        # Training mode requires RAG, roleplay can work without it
        raise ValidationError(
            "RAG not initialized for your dealership. Please contact your dealership admin."
        )

    # Generate response using LLM
    response_text = await llm_service.generate_with_context(
        query=chat_message.message,
        context=context,
        mode=chat_message.mode.value,
        conversation_history=chat_message.conversation_history,
    )

    # Generate or use existing session ID
    session_id = (
        chat_message.session_id
        or f"session_{current_user.id}_{datetime.utcnow().timestamp()}"
    )

    # Format sources
    sources = (
        [
            {
                "topic": doc.get("topic", "Unknown"),
                "filename": doc.get("filename", ""),
                "relevance": f"{doc.get('score', 0):.2f}",
            }
            for doc in context_docs
        ]
        if context_docs
        else None
    )

    return ChatResponse(
        response=response_text,
        session_id=session_id,
        sources=sources,
        timestamp=datetime.utcnow(),
    )


@router.get(
    "/history", response_model=list[ChatResponse], status_code=status.HTTP_200_OK
)
async def get_chat_history(
    session_id: str | None = None,
    limit: int = 50,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
) -> list[ChatResponse]:
    """
    Get chat history for current user.

    Args:
        session_id: Optional session ID to filter by
        limit: Maximum number of messages to return
        db: Database session
        current_user: Current authenticated user

    Returns:
        List of chat messages
    """
    # TODO: Implement chat history retrieval from database
    return []


class PrewarmRequest(BaseModel):
    """Request to pre-warm RAG context for a voice session."""

    session_id: str = Field(..., description="Session ID for the voice call")
    dealership_id: int | None = Field(
        None, description="Dealership ID (required for super admin)"
    )


class PrewarmResponse(BaseModel):
    """Response from pre-warming RAG context."""

    session_id: str
    dealership_id: int
    chunks_prewarmed: int
    queries_run: int
    elapsed_ms: float


@router.post("/prewarm", response_model=PrewarmResponse, status_code=status.HTTP_200_OK)
async def prewarm_rag_context(
    request: PrewarmRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> PrewarmResponse:
    """
    Pre-warm RAG context for a voice call session.

    Call this when a voice call starts to reduce latency on the first queries.
    Pre-fetches common F&I knowledge and stores it in session cache.

    Args:
        request: Pre-warm request with session ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        Stats about pre-warmed content
    """
    # Determine dealership ID based on user role
    if current_user.role == UserRole.SUPER_ADMIN:
        if not request.dealership_id:
            raise ValidationError("Super admin must specify dealership_id")
        dealership_id = request.dealership_id
    else:
        if not current_user.dealership_id:
            raise ValidationError("User must be associated with a dealership")
        dealership_id = current_user.dealership_id
        if request.dealership_id and request.dealership_id != dealership_id:
            raise AuthorizationError("You can only pre-warm for your own dealership")

    # Verify dealership exists and has RAG
    result = await db.execute(select(Dealership).where(Dealership.id == dealership_id))
    dealership = result.scalar_one_or_none()

    if not dealership:
        raise NotFoundError("Dealership not found")

    if not dealership.rag_config:
        raise ValidationError("RAG not initialized for this dealership")

    # Pre-warm session
    rag_service = get_rag_service()
    stats = await rag_service.prewarm_session(
        session_id=request.session_id,
        dealership_id=dealership_id,
    )

    return PrewarmResponse(**stats)


@router.post("/session/{session_id}/clear", status_code=status.HTTP_200_OK)
async def clear_session_context(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> dict:
    """
    Clear RAG session context when a voice call ends.

    Args:
        session_id: Session ID to clear
        current_user: Current authenticated user

    Returns:
        Success message
    """
    rag_service = get_rag_service()
    await rag_service.clear_session(session_id)
    return {"message": f"Session {session_id} context cleared"}


@router.get("/cache/stats", status_code=status.HTTP_200_OK)
async def get_cache_stats(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> dict:
    """
    Get RAG cache statistics (admin only).

    Returns cache hit rates and memory usage for monitoring.

    Args:
        current_user: Current authenticated user (must be admin)

    Returns:
        Cache statistics
    """
    if current_user.role != UserRole.SUPER_ADMIN:
        raise AuthorizationError("Only super admin can view cache stats")

    from app.services.rag_cache import get_rag_cache

    cache = get_rag_cache()
    return cache.stats()
