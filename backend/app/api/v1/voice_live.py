"""
Production-ready Live Voice Chat WebSocket endpoint.

This module provides a clean implementation of real-time voice chat
using OpenAI Whisper for STT and ElevenLabs for TTS.
"""

import asyncio
import base64
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.realtime_voice_service import get_realtime_voice_service

logger = logging.getLogger(__name__)

router = APIRouter()


class LiveVoiceSession:
    """
    Manages a single live voice chat session.
    
    Handles:
    - WebSocket connection to client
    - Audio buffering and STT via OpenAI Whisper
    - Response generation and TTS via ElevenLabs
    - Conversation history
    """
    
    def __init__(self, websocket: WebSocket, user_id: int):
        self.websocket = websocket
        self.user_id = user_id
        self.mode = "training"
        self.conversation_history: list[dict] = []
        self.is_processing = False
        self.is_active = True
        self.realtime_service = get_realtime_voice_service()
        self._process_lock = asyncio.Lock()
        self._audio_buffer: list[bytes] = []
        self._is_recording = False
    
    async def send_json(self, payload: dict) -> bool:
        """Send JSON to client. Returns False if connection is closed."""
        if not self.is_active:
            return False
        try:
            await self.websocket.send_json(payload)
            return True
        except (WebSocketDisconnect, RuntimeError):
            self.is_active = False
            return False
    
    def start_recording(self):
        """Start buffering audio."""
        self._audio_buffer = []
        self._is_recording = True
    
    def add_audio_chunk(self, audio_data: bytes):
        """Add audio chunk to buffer."""
        if self._is_recording:
            self._audio_buffer.append(audio_data)
    
    def stop_recording(self) -> bytes:
        """Stop recording and return buffered audio."""
        self._is_recording = False
        if self._audio_buffer:
            audio = b"".join(self._audio_buffer)
            self._audio_buffer = []
            return audio
        return b""
    
    async def process_audio(self, audio_data: bytes, use_streaming: bool = True) -> None:
        """
        Process audio data and generate response with streaming TTS.
        Uses a lock to prevent duplicate processing.
        
        Args:
            use_streaming: If True, streams audio chunks as they're generated.
                          This provides the lowest latency - audio starts playing
                          while the LLM is still generating text!
        """
        async with self._process_lock:
            if self.is_processing or not audio_data or not self.is_active:
                return
            
            self.is_processing = True
            
        try:
            await self.send_json({"type": "processing"})
            
            # Use the streaming pipeline
            full_response = ""
            user_transcript = ""
            
            async for chunk in self.realtime_service.process_voice_streaming(
                audio_data=audio_data,
                mode=self.mode,
                conversation_history=self.conversation_history,
                use_websocket_tts=use_streaming,
            ):
                if chunk["type"] == "transcript":
                    user_transcript = chunk["text"]
                    await self.send_json({
                        "type": "transcript",
                        "text": user_transcript,
                        "is_final": True,
                        "full_transcript": user_transcript,
                    })
                
                elif chunk["type"] == "audio_chunk":
                    # Streaming audio chunk - send immediately for playback
                    await self.send_json({
                        "type": "audio_chunk",
                        "data": chunk["data"],
                    })
                
                elif chunk["type"] == "audio":
                    # Complete audio (fallback mode)
                    await self.send_json({
                        "type": "audio",
                        "data": chunk["data"],
                    })
                
                elif chunk["type"] == "done":
                    full_response = chunk["text"]
                    await self.send_json({
                        "type": "response_complete",
                        "text": full_response,
                        "user_text": user_transcript,
                    })
                
                elif chunk["type"] == "error":
                    await self.send_json({
                        "type": "error",
                        "message": chunk["message"],
                    })
                    return
            
            # Update conversation history
            if full_response and user_transcript:
                self.conversation_history.append({"role": "user", "content": user_transcript})
                self.conversation_history.append({"role": "assistant", "content": full_response})
                
                # Keep history manageable
                if len(self.conversation_history) > 10:
                    self.conversation_history = self.conversation_history[-10:]
                    
        except Exception as e:
            logger.error(f"[LiveVoice] Error processing audio: {e}")
            await self.send_json({"type": "error", "message": str(e)})
        finally:
            self.is_processing = False
            await self.send_json({"type": "ready"})


@router.websocket("/ws/live/{user_id}")
async def voice_chat_live(websocket: WebSocket, user_id: int):
    """
    Live voice chat WebSocket endpoint.
    
    Protocol:
    1. Client connects and sends: {"type": "init", "mode": "training|roleplay"}
    2. Client sends: {"type": "start_recording"} when user starts speaking
    3. Client streams audio: {"type": "audio", "data": "<base64>"} or raw bytes
    4. Client sends: {"type": "stop_recording"} when user stops speaking
    5. Server processes audio and sends response
    
    Message types from server:
    - {"type": "ready"} - Ready to receive audio
    - {"type": "transcript", "text": "...", "is_final": bool, "full_transcript": "..."}
    - {"type": "processing"} - Generating response
    - {"type": "response", "text": "...", "audio": "<base64>", "user_text": "..."}
    - {"type": "error", "message": "..."}
    """
    await websocket.accept()
    session = LiveVoiceSession(websocket, user_id)
    logger.info(f"[LiveVoice] Session started for user {user_id}")
    
    try:
        # Wait for init message with timeout
        try:
            init_msg = await asyncio.wait_for(
                websocket.receive_json(),
                timeout=10.0
            )
            if init_msg.get("type") == "init":
                session.mode = init_msg.get("mode", "training")
                logger.info(f"[LiveVoice] User {user_id} initialized with mode={session.mode}")
        except asyncio.TimeoutError:
            await session.send_json({"type": "error", "message": "Init timeout"})
            return
        
        # Notify client we're ready
        await session.send_json({"type": "ready", "message": "Listening..."})
        
        # Main loop: receive audio from client
        while session.is_active:
            try:
                message = await websocket.receive()
                
                if message["type"] == "websocket.disconnect":
                    break
                
                if message["type"] == "websocket.receive":
                    if "bytes" in message:
                        # Raw audio bytes - add to buffer
                        session.add_audio_chunk(message["bytes"])
                    elif "text" in message:
                        import json
                        data = json.loads(message["text"])
                        msg_type = data.get("type")
                        
                        if msg_type == "start_recording":
                            session.start_recording()
                            await session.send_json({"type": "speaking_started"})
                        
                        elif msg_type == "stop_recording":
                            audio_data = session.stop_recording()
                            await session.send_json({"type": "speaking_stopped"})
                            if audio_data:
                                asyncio.create_task(session.process_audio(audio_data))
                        
                        elif msg_type == "audio":
                            # Base64 encoded audio chunk
                            audio_chunk = base64.b64decode(data.get("data", ""))
                            session.add_audio_chunk(audio_chunk)
                        
                        elif msg_type == "audio_complete":
                            # Complete audio in one message (alternative to streaming)
                            audio_data = base64.b64decode(data.get("data", ""))
                            if audio_data:
                                asyncio.create_task(session.process_audio(audio_data))
                        
                        elif msg_type == "clear":
                            session.conversation_history.clear()
                            await session.send_json({"type": "cleared"})
                        
                        elif msg_type == "ping":
                            await session.send_json({"type": "pong"})
                        
                        elif msg_type == "mode":
                            session.mode = data.get("mode", session.mode)
                            await session.send_json({"type": "mode_changed", "mode": session.mode})
            
            except WebSocketDisconnect:
                break
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[LiveVoice] Error in main loop: {e}")
                await session.send_json({"type": "error", "message": str(e)})
                break
    
    except WebSocketDisconnect:
        logger.info(f"[LiveVoice] User {user_id} disconnected")
    except Exception as e:
        logger.error(f"[LiveVoice] Session error for user {user_id}: {e}")
    finally:
        session.is_active = False
        logger.info(f"[LiveVoice] Session ended for user {user_id}")
