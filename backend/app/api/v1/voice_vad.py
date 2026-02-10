"""Voice Activity Detection WebSocket endpoint."""

import base64
import json
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.services.vad_service import get_vad_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["voice"])


class VADWebSocketManager:
    """Manages WebSocket connections for VAD."""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept a WebSocket connection."""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"VAD WebSocket connected: {client_id}")

    def disconnect(self, client_id: str):
        """Disconnect a WebSocket connection."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"VAD WebSocket disconnected: {client_id}")

    async def send_vad_event(self, client_id: str, event: dict):
        """Send a VAD event to a client."""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(event)
            except Exception as e:
                logger.error(f"Error sending VAD event to {client_id}: {e}")
                self.disconnect(client_id)


vad_manager = VADWebSocketManager()


@router.websocket("/ws/vad/{client_id}")
async def websocket_vad(websocket: WebSocket, client_id: str):
    """
    WebSocket endpoint for real-time Voice Activity Detection.
    
    Client sends:
    {
        "type": "audio_frame",
        "data": "base64_encoded_audio",
        "sample_rate": 16000,
        "aggressiveness": 2
    }
    
    Server sends:
    {
        "type": "vad_event",
        "is_speech": bool,
        "confidence": float,
        "speech_started": bool,
        "speech_ended": bool,
        "duration_ms": int
    }
    """
    await vad_manager.connect(websocket, client_id)
    vad = get_vad_manager()
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "audio_frame":
                try:
                    # Decode audio data
                    audio_bytes = base64.b64decode(message.get("data", ""))
                    sample_rate = message.get("sample_rate", 16000)
                    aggressiveness = message.get("aggressiveness", 2)
                    
                    # Process frame
                    detector = vad.get_detector(
                        client_id,
                        sample_rate=sample_rate,
                        aggressiveness=aggressiveness,
                    )
                    result = detector.process_frame(audio_bytes)
                    
                    # Send VAD event back to client
                    await vad_manager.send_vad_event(
                        client_id,
                        {
                            "type": "vad_event",
                            **result,
                        },
                    )
                    
                except Exception as e:
                    logger.error(f"Error processing audio frame: {e}")
                    await vad_manager.send_vad_event(
                        client_id,
                        {
                            "type": "error",
                            "message": str(e),
                        },
                    )
            
            elif message.get("type") == "reset":
                # Reset VAD state
                vad.reset_detector(client_id)
                await vad_manager.send_vad_event(
                    client_id,
                    {
                        "type": "reset_ack",
                    },
                )
            
            elif message.get("type") == "ping":
                # Respond to ping
                await vad_manager.send_vad_event(
                    client_id,
                    {
                        "type": "pong",
                    },
                )
    
    except WebSocketDisconnect:
        vad_manager.disconnect(client_id)
        vad.remove_detector(client_id)
        logger.info(f"VAD WebSocket disconnected: {client_id}")
    
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
        vad_manager.disconnect(client_id)
        vad.remove_detector(client_id)


@router.post("/vad/process")
async def process_audio_vad(
    audio_data: bytes,
    sample_rate: int = 16000,
    aggressiveness: int = 2,
):
    """
    Process audio for VAD (non-streaming endpoint).
    
    Returns VAD results for the audio chunk.
    """
    try:
        vad = get_vad_manager()
        detector = vad.get_detector(
            "temp",
            sample_rate=sample_rate,
            aggressiveness=aggressiveness,
        )
        
        results = detector.process_audio_chunk(audio_data)
        
        # Clean up temp detector
        vad.remove_detector("temp")
        
        return {
            "success": True,
            "results": results,
            "frame_count": len(results),
        }
    
    except Exception as e:
        logger.error(f"Error processing audio: {e}")
        return {
            "success": False,
            "error": str(e),
        }
