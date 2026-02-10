"""Voice chat endpoints using ElevenLabs for TTS and OpenAI Whisper for STT."""

import asyncio
import base64
import json
from contextlib import suppress
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db, require_websocket_auth
from app.middleware.rate_limit import limiter, VOICE_LIMIT
from app.core.database import get_db as get_db_session
from app.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.models.dealership import Dealership
from app.models.user import User, UserRole
from app.services.llm_service import get_llm_service
from app.services.rag_service import get_rag_service
from app.services.voice_service import VoiceChatSession, get_voice_service
from app.services.realtime_voice_service import get_realtime_voice_service

router = APIRouter()


class VoiceChatRequest(BaseModel):
    """Voice chat request schema."""

    audio_base64: str = Field(..., description="Base64-encoded audio data")
    mode: str = Field(default="training", description="Chat mode: training or roleplay")
    session_id: str | None = Field(
        None, description="Session ID for conversation context"
    )
    mime_type: str = Field(default="audio/wav", description="Audio MIME type")
    dealership_id: int | None = Field(
        None, description="Dealership ID (required for super admin)"
    )


class VoiceChatResponse(BaseModel):
    """Voice chat response schema."""

    user_transcript: str = Field(..., description="Transcribed user speech")
    response_text: str = Field(..., description="AI text response")
    response_audio_base64: str = Field(..., description="Base64-encoded audio response")
    session_id: str = Field(..., description="Session ID")
    confidence: float = Field(..., description="Transcription confidence score")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TTSRequest(BaseModel):
    """Text-to-speech request schema."""

    text: str = Field(
        ..., min_length=1, max_length=5000, description="Text to convert to speech"
    )
    voice_id: str | None = Field(
        None, description="Optional ElevenLabs voice ID override"
    )


class TTSResponse(BaseModel):
    """Text-to-speech response schema."""

    audio_base64: str = Field(..., description="Base64-encoded audio")
    text: str = Field(..., description="Original text")


class STTRequest(BaseModel):
    """Speech-to-text request schema."""

    audio_base64: str = Field(..., description="Base64-encoded audio data")
    mime_type: str = Field(default="audio/wav", description="Audio MIME type")
    language: str = Field(default="en", description="Language code")


class STTResponse(BaseModel):
    """Speech-to-text response schema."""

    transcript: str = Field(..., description="Transcribed text")
    confidence: float = Field(..., description="Confidence score")
    words: list[dict] | None = Field(None, description="Word-level timestamps")


# Store for voice chat sessions
_voice_sessions: dict[str, VoiceChatSession] = {}


@router.post("/chat", response_model=VoiceChatResponse, status_code=status.HTTP_200_OK)
@limiter.limit(VOICE_LIMIT)
async def voice_chat(
    request: Request,
    voice_request: VoiceChatRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> VoiceChatResponse:
    """
    Voice chat endpoint - send audio, receive audio response.

    Process:
    1. Transcribe user audio using OpenAI Whisper STT
    2. Query RAG for context (training mode)
    3. Generate response using LLM
    4. Convert response to speech using ElevenLabs TTS

    Args:
        http_request: FastAPI request object (required for rate limiting)
        request: Voice chat request with audio data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Voice chat response with transcript and audio
    """
    # Determine dealership ID based on user role
    if current_user.role == UserRole.SUPER_ADMIN:
        # Super admin must provide dealership_id
        if not voice_request.dealership_id:
            raise ValidationError("Super admin must specify dealership_id")
        dealership_id = voice_request.dealership_id
    else:
        # Regular users use their assigned dealership
        if not current_user.dealership_id:
            raise ValidationError(
                "User must be associated with a dealership to use voice chat"
            )
        dealership_id = current_user.dealership_id

        # If dealership_id is provided, ensure it matches user's dealership
        if voice_request.dealership_id and voice_request.dealership_id != dealership_id:
            raise AuthorizationError(
                "You can only use voice chat for your own dealership"
            )

    # Get dealership
    result = await db.execute(select(Dealership).where(Dealership.id == dealership_id))
    dealership = result.scalar_one_or_none()

    if not dealership:
        raise NotFoundError("Dealership not found")

    # Training mode requires RAG
    if voice_request.mode == "training" and not dealership.rag_config:
        raise ValidationError(
            "RAG not initialized for your dealership. Please contact your dealership admin."
        )

    # Get or create session
    session_id = (
        voice_request.session_id or f"voice_{current_user.id}_{datetime.utcnow().timestamp()}"
    )

    if session_id not in _voice_sessions:
        voice_service = get_voice_service()
        llm_service = get_llm_service()
        rag_service = get_rag_service()

        # Create callbacks
        async def llm_callback(
            text: str,
            context: str = "",
            mode: str = "training",
            conversation_history: list[dict] | None = None,
        ) -> str:
            return await llm_service.generate_with_context(
                query=text,
                context=context,
                mode=mode,
                conversation_history=conversation_history,
            )

        async def rag_callback(query: str, mode: str = "training") -> str:
            if not dealership.rag_config:
                return ""

            # OPTIMIZED: Direct semantic search - no topic classification needed
            # This saves ~300-500ms by removing the topic classification LLM call
            # Pinecone's semantic similarity search already ranks results by relevance
            docs = await rag_service.query(
                query=query,
                dealership_id=dealership.id,
                topics=None,  # Search all topics, semantic similarity will rank them
                top_k=5,
            )

            if not docs:
                return ""

            # Format context with topic metadata for better LLM understanding
            context_parts = []
            for doc in docs:
                topic = doc.get("topic", "unknown")
                filename = doc.get("filename", "")
                content = doc.get("content", "")
                score = doc.get("score", 0)

                # Include metadata in context for better responses
                context_parts.append(
                    f"[Source: {topic} | File: {filename} | Relevance: {score:.2f}]\n{content}"
                )

            return "\n\n---\n\n".join(context_parts)

        # Both training and roleplay can benefit from RAG context
        _voice_sessions[session_id] = VoiceChatSession(
            voice_service=voice_service,
            llm_callback=llm_callback,
            rag_callback=rag_callback if dealership.rag_config else None,
        )

    session = _voice_sessions[session_id]

    # Decode audio
    try:
        audio_data = base64.b64decode(voice_request.audio_base64)
    except Exception:
        raise ValidationError("Invalid base64 audio data")

    # Process audio
    result = await session.process_audio(
        audio_data=audio_data,
        mode=voice_request.mode,
    )

    return VoiceChatResponse(
        user_transcript=result["user_transcript"],
        response_text=result["response_text"],
        response_audio_base64=result["response_audio"],
        session_id=session_id,
        confidence=result.get("confidence", 0.0),
        timestamp=datetime.utcnow(),
    )


# Store for fast voice sessions (separate from regular sessions for history)
_fast_sessions: dict[str, dict] = {}


@router.post(
    "/chat/fast", response_model=VoiceChatResponse, status_code=status.HTTP_200_OK
)
@limiter.limit(VOICE_LIMIT)
async def voice_chat_fast(
    request: Request,
    voice_request: VoiceChatRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> VoiceChatResponse:
    """
    Ultra-fast voice chat endpoint - optimized for minimal latency.

    Optimizations:
    - NO RAG queries (uses conversation context only)
    - Single STT call
    - Short LLM responses (max 100 tokens)
    - Minimal conversation history (last 4 messages)

    Use /chat for full RAG-powered responses.

    Args:
        http_request: FastAPI request object (required for rate limiting)
        request: Voice chat request with audio data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Voice chat response with transcript and audio
    """
    # Determine dealership ID based on user role
    if current_user.role == UserRole.SUPER_ADMIN:
        if not voice_request.dealership_id:
            raise ValidationError("Super admin must specify dealership_id")
        dealership_id = voice_request.dealership_id
    else:
        if not current_user.dealership_id:
            raise ValidationError(
                "User must be associated with a dealership to use voice chat"
            )
        dealership_id = current_user.dealership_id
        if voice_request.dealership_id and voice_request.dealership_id != dealership_id:
            raise AuthorizationError(
                "You can only use voice chat for your own dealership"
            )

    # Verify dealership exists (lightweight check)
    result = await db.execute(
        select(Dealership.id).where(Dealership.id == dealership_id)
    )
    if not result.scalar_one_or_none():
        raise NotFoundError("Dealership not found")

    # Get or create fast session
    session_id = (
        voice_request.session_id or f"fast_{current_user.id}_{datetime.utcnow().timestamp()}"
    )

    if session_id not in _fast_sessions:
        _fast_sessions[session_id] = {"history": [], "dealership_id": dealership_id}

    session = _fast_sessions[session_id]

    # Decode audio
    try:
        audio_data = base64.b64decode(voice_request.audio_base64)
    except Exception:
        raise ValidationError("Invalid base64 audio data")

    # Use realtime voice service for fast processing (NO RAG for speed)
    realtime_service = get_realtime_voice_service()
    result = await realtime_service.process_voice_fast(
        audio_data=audio_data,
        mode=voice_request.mode,
        context="",  # No RAG context for speed
        conversation_history=session["history"],
        mime_type=voice_request.mime_type,
    )

    # Update session history
    if result["transcript"]:
        session["history"].append({"role": "user", "content": result["transcript"]})
        session["history"].append({"role": "assistant", "content": result["response"]})
        # Keep only last 4 messages for fast sessions
        if len(session["history"]) > 4:
            session["history"] = session["history"][-4:]

    return VoiceChatResponse(
        user_transcript=result["transcript"],
        response_text=result["response"],
        response_audio_base64=base64.b64encode(result["audio"]).decode("utf-8"),
        session_id=session_id,
        confidence=result.get("confidence", 0.0),
        timestamp=datetime.utcnow(),
    )


@router.post("/tts", response_model=TTSResponse, status_code=status.HTTP_200_OK)
async def text_to_speech(
    request: TTSRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> TTSResponse:
    """
    Convert text to speech using ElevenLabs.

    Args:
        request: TTS request with text
        current_user: Current authenticated user

    Returns:
        Base64-encoded audio response
    """
    voice_service = get_voice_service()

    audio_base64 = await voice_service.text_to_speech_base64(
        text=request.text,
        voice_id=request.voice_id,
    )

    return TTSResponse(
        audio_base64=audio_base64,
        text=request.text,
    )


@router.post("/stt", response_model=STTResponse, status_code=status.HTTP_200_OK)
async def speech_to_text(
    request: STTRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> STTResponse:
    """
    Convert speech to text using OpenAI Whisper.

    Args:
        request: STT request with audio
        current_user: Current authenticated user

    Returns:
        Transcription result
    """
    voice_service = get_voice_service()

    # Decode audio
    try:
        audio_data = base64.b64decode(request.audio_base64)
    except Exception:
        raise ValidationError("Invalid base64 audio data")

    result = await voice_service.transcribe_audio(
        audio_data=audio_data,
        mime_type=request.mime_type,
        language=request.language,
    )

    return STTResponse(
        transcript=result["transcript"],
        confidence=result["confidence"],
        words=result.get("words"),
    )


@router.delete("/session/{session_id}", status_code=status.HTTP_200_OK)
async def clear_session(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> dict:
    """
    Clear a voice chat session.

    Args:
        session_id: Session ID to clear
        current_user: Current authenticated user

    Returns:
        Success message
    """
    # Security: Verify session ownership
    # Session IDs contain user_id: "voice_{user_id}_timestamp" or "fast_{user_id}_timestamp"
    session_parts = session_id.split("_")
    if len(session_parts) >= 2:
        try:
            session_user_id = int(session_parts[1])
            if session_user_id != current_user.id:
                raise AuthorizationError("You can only clear your own sessions")
        except ValueError:
            pass  # Invalid format, allow deletion (might be old format)

    if session_id in _voice_sessions:
        _voice_sessions[session_id].clear_history()
        del _voice_sessions[session_id]

    if session_id in _fast_sessions:
        del _fast_sessions[session_id]

    return {"message": f"Session {session_id} cleared"}


@router.websocket("/ws/stream/{user_id}")
async def voice_chat_stream_websocket(
    websocket: WebSocket,
    user_id: int,
):
    """
    Streaming WebSocket for real-time voice chat.

    Sends audio chunks as sentences are generated - much faster perceived latency.

    Authentication:
    - Requires JWT token via query parameter: ?token=<jwt_token>
    - The user_id in the URL must match the authenticated user

    Protocol:
    1. Client sends: {"type": "init", "mode": "training|roleplay"}
    2. Client sends: {"type": "audio", "data": "<base64>"}
    3. Server streams: {"type": "audio", "data": "<base64>"} - multiple times
    4. Server sends: {"type": "done"}
    """
    # Authenticate before accepting connection
    try:
        current_user = await require_websocket_auth(websocket, user_id)
    except Exception:
        return  # Connection already closed by require_websocket_auth

    await websocket.accept()

    realtime_service = get_realtime_voice_service()
    conversation_history: list[dict] = []
    mode = "training"

    try:
        while True:
            message = await websocket.receive_json()
            msg_type = message.get("type")

            if msg_type == "init":
                mode = message.get("mode", "training")
                await websocket.send_json({"type": "ready"})

            elif msg_type == "audio":
                audio_base64 = message.get("data", "")
                current_mode = message.get("mode", mode)

                try:
                    audio_data = base64.b64decode(audio_base64)

                    # Stream response - sends audio chunks as they're ready
                    full_response = ""
                    async for chunk in realtime_service.process_voice_streaming(
                        audio_data=audio_data,
                        mode=current_mode,
                        conversation_history=conversation_history,
                    ):
                        if chunk["type"] == "transcript":
                            await websocket.send_json(
                                {"type": "transcript", "text": chunk["text"]}
                            )
                        elif chunk["type"] == "audio":
                            await websocket.send_json(
                                {"type": "audio", "data": chunk["data"]}
                            )
                        elif chunk["type"] == "error":
                            await websocket.send_json(
                                {"type": "error", "message": chunk["message"]}
                            )
                            break
                        elif chunk["type"] == "done":
                            full_response = chunk["text"]
                            await websocket.send_json({"type": "done"})

                    # Update history
                    if full_response:
                        conversation_history.append(
                            {"role": "user", "content": message.get("transcript", "")}
                        )
                        conversation_history.append(
                            {"role": "assistant", "content": full_response}
                        )
                        if len(conversation_history) > 8:
                            conversation_history = conversation_history[-8:]

                except Exception as e:
                    await websocket.send_json({"type": "error", "message": str(e)})

            elif msg_type == "clear":
                conversation_history = []
                await websocket.send_json({"type": "cleared"})

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        pass
    except Exception:
        pass


@router.websocket("/ws/{user_id}")
async def voice_chat_websocket(
    websocket: WebSocket,
    user_id: int,
):
    """
    Legacy WebSocket endpoint for voice chat.
    Use /ws/stream/{user_id} for streaming responses.

    Authentication:
    - Requires JWT token via query parameter: ?token=<jwt_token>
    - The user_id in the URL must match the authenticated user
    """
    # Authenticate before accepting connection
    try:
        current_user = await require_websocket_auth(websocket, user_id)
    except Exception:
        return  # Connection already closed by require_websocket_auth

    await websocket.accept()

    realtime_service = get_realtime_voice_service()
    conversation_history: list[dict] = []

    try:
        init_message = await websocket.receive_json()
        mode = init_message.get("mode", "training")

        await websocket.send_json(
            {
                "type": "connected",
                "message": "Voice chat session started",
            }
        )

        while True:
            message = await websocket.receive_json()

            if message.get("type") == "audio":
                audio_base64 = message.get("data", "")
                current_mode = message.get("mode", mode)

                try:
                    audio_data = base64.b64decode(audio_base64)

                    result = await realtime_service.process_voice_fast(
                        audio_data=audio_data,
                        mode=current_mode,
                        conversation_history=conversation_history,
                    )

                    if result["transcript"]:
                        conversation_history.append(
                            {"role": "user", "content": result["transcript"]}
                        )
                        conversation_history.append(
                            {"role": "assistant", "content": result["response"]}
                        )
                        if len(conversation_history) > 8:
                            conversation_history = conversation_history[-8:]

                    await websocket.send_json(
                        {
                            "type": "response",
                            "transcript": result["transcript"],
                            "audio": base64.b64encode(result["audio"]).decode(),
                        }
                    )

                except Exception as e:
                    await websocket.send_json({"type": "error", "message": str(e)})

            elif message.get("type") == "clear":
                conversation_history = []
                await websocket.send_json({"type": "cleared"})

            elif message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        pass
    except Exception:
        pass


@router.websocket("/ws/live/{user_id}")
async def voice_chat_live_websocket(
    websocket: WebSocket,
    user_id: int,
):
    """
    Live voice chat WebSocket endpoint.

    This endpoint provides voice chat with audio buffering:
    - Client sends start_recording when user starts speaking
    - Client streams audio chunks
    - Client sends stop_recording when user stops speaking
    - Server transcribes and generates response

    Authentication:
    - Requires JWT token via query parameter: ?token=<jwt_token>
    - The user_id in the URL must match the authenticated user

    Protocol:
    1. Client sends: {"type": "init", "mode": "training|roleplay"}
    2. Client sends: {"type": "start_recording"} when user starts speaking
    3. Client streams: {"type": "audio", "data": "<base64>"} or raw bytes
    4. Client sends: {"type": "stop_recording"} when user stops speaking
    5. Server sends: {"type": "transcript", "text": "...", "is_final": true}
    6. Server sends: {"type": "response", "text": "...", "audio": "<base64>"}
    """
    import logging

    logger = logging.getLogger(__name__)

    # Authenticate before accepting connection
    try:
        current_user = await require_websocket_auth(websocket, user_id)
    except Exception:
        logger.warning(f"[VOICE WS] Authentication failed for user_id {user_id}")
        return  # Connection already closed by require_websocket_auth

    await websocket.accept()
    logger.info(f"[VOICE WS] WebSocket accepted for authenticated user {user_id}")

    realtime_service = get_realtime_voice_service()
    conversation_history: list[dict] = []
    mode = "training"
    audio_buffer: list[bytes] = []
    is_recording = False
    is_processing = False
    is_interrupted = False  # Flag to cancel current processing when user interrupts
    websocket_active = True

    async def send_json_safe(payload: dict):
        """Send JSON to client, ignoring disconnects."""
        nonlocal websocket_active
        if not websocket_active:
            return
        try:
            await websocket.send_json(payload)
        except WebSocketDisconnect:
            websocket_active = False
        except RuntimeError:
            websocket_active = False

    async def process_audio(audio_data: bytes):
        """Process the audio and generate response."""
        nonlocal is_processing, is_interrupted

        if is_processing or not audio_data:
            return

        is_processing = True
        is_interrupted = False  # Reset interrupt flag for new processing

        try:
            await send_json_safe({"type": "processing"})

            # Check for interrupt before transcription
            if is_interrupted:
                logger.info("[VOICE WS] Processing interrupted before transcription")
                return

            # Transcribe audio using Whisper
            stt_result = await realtime_service.transcribe_audio_fast(audio_data)
            transcript = stt_result.get("transcript", "").strip()

            if stt_result.get("error"):
                await send_json_safe(
                    {
                        "type": "error",
                        "message": f"Speech recognition failed: {stt_result['error']}",
                    }
                )
                return

            # Check for interrupt after transcription
            if is_interrupted:
                logger.info("[VOICE WS] Processing interrupted after transcription")
                return

            await send_json_safe(
                {
                    "type": "transcript",
                    "text": transcript,
                    "is_final": True,
                    "full_transcript": transcript,
                }
            )

            if not transcript:
                return

            # Generate and stream response (check for interrupt during generation)
            full_response = ""
            async for chunk in realtime_service.generate_response_stream(
                query=transcript,
                mode=mode,
                conversation_history=conversation_history,
            ):
                if is_interrupted:
                    logger.info("[VOICE WS] Processing interrupted during LLM generation")
                    return
                full_response += chunk

            # Check for interrupt before TTS
            if is_interrupted:
                logger.info("[VOICE WS] Processing interrupted before TTS")
                return

            # Generate TTS for the response
            if full_response:
                audio = await realtime_service.text_to_speech(full_response)
                
                # Final interrupt check before sending audio
                if is_interrupted:
                    logger.info("[VOICE WS] Processing interrupted before sending audio")
                    return
                    
                await send_json_safe(
                    {
                        "type": "audio",
                        "data": base64.b64encode(audio).decode(),
                        "text": full_response,
                    }
                )

                # Update conversation history
                conversation_history.append({"role": "user", "content": transcript})
                conversation_history.append(
                    {"role": "assistant", "content": full_response}
                )
                if len(conversation_history) > 8:
                    conversation_history[:] = conversation_history[-8:]

        except Exception as e:
            if not is_interrupted:  # Don't send error if we were just interrupted
                await send_json_safe({"type": "error", "message": str(e)})
        finally:
            is_processing = False
            if not is_interrupted:
                await send_json_safe({"type": "ready"})

    try:
        # Wait for init message
        logger.info(f"[VOICE WS] Waiting for init message from user {user_id}")
        init_msg = await websocket.receive_json()
        if init_msg.get("type") == "init":
            mode = init_msg.get("mode", "training")

        logger.info(f"[VOICE WS] User {user_id} initialized with mode={mode}")
        await send_json_safe({"type": "ready", "message": "Listening..."})

        # Main loop
        while websocket_active:
            try:
                message = await websocket.receive()

                if message["type"] == "websocket.receive":
                    if "bytes" in message:
                        # Raw audio bytes - add to buffer if recording
                        if is_recording:
                            audio_buffer.append(message["bytes"])
                    elif "text" in message:
                        data = json.loads(message["text"])
                        msg_type = data.get("type")

                        if msg_type == "start_recording":
                            audio_buffer = []
                            is_recording = True
                            is_interrupted = False  # Reset interrupt flag for new recording
                            await send_json_safe({"type": "speaking_started"})

                        elif msg_type == "stop_recording":
                            is_recording = False
                            await send_json_safe({"type": "speaking_stopped"})
                            if audio_buffer:
                                audio_data = b"".join(audio_buffer)
                                audio_buffer = []
                                asyncio.create_task(process_audio(audio_data))

                        elif msg_type == "audio":
                            # Base64 encoded audio chunk
                            if is_recording:
                                audio_chunk = base64.b64decode(data.get("data", ""))
                                audio_buffer.append(audio_chunk)

                        elif msg_type == "audio_complete":
                            # Complete audio in one message
                            audio_data = base64.b64decode(data.get("data", ""))
                            if audio_data:
                                asyncio.create_task(process_audio(audio_data))

                        elif msg_type == "interrupt":
                            # User is interrupting Adam's response
                            logger.info("[VOICE WS] User interrupt received - canceling current processing")
                            is_interrupted = True
                            audio_buffer = []  # Clear any buffered audio
                            await send_json_safe({"type": "interrupted"})

                        elif msg_type == "clear":
                            conversation_history.clear()
                            audio_buffer = []
                            is_interrupted = True  # Also interrupt any ongoing processing
                            await send_json_safe({"type": "cleared"})

                        elif msg_type == "ping":
                            await send_json_safe({"type": "pong"})

                        elif msg_type == "mode":
                            mode = data.get("mode", mode)
                            await send_json_safe({"type": "mode_changed", "mode": mode})

                elif message["type"] == "websocket.disconnect":
                    break

            except WebSocketDisconnect:
                logger.info("[VOICE WS] Client disconnected (WebSocketDisconnect)")
                break
            except asyncio.CancelledError:
                logger.info("[VOICE WS] Cancelled")
                break
            except Exception as e:
                logger.error(f"[VOICE WS] Error in main loop: {e}")
                await send_json_safe({"type": "error", "message": str(e)})
                break

        logger.info("[VOICE WS] Exited main loop")

    except WebSocketDisconnect:
        logger.info("[VOICE WS] Outer WebSocketDisconnect")
        pass
    except asyncio.CancelledError:
        logger.info("[VOICE WS] Outer CancelledError")
        pass
    except Exception as e:
        logger.error(f"[VOICE WS] Outer exception: {e}")
        try:
            await send_json_safe({"type": "error", "message": str(e)})
        except:
            pass
    finally:
        logger.info("[VOICE WS] Cleanup")
        websocket_active = False
