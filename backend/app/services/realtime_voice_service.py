"""Real-time voice service with streaming STT/LLM/TTS for low latency."""

import asyncio
import base64
import io
import json
import logging
import struct
import wave
from typing import AsyncGenerator

import httpx
import websockets
from openai import AsyncOpenAI

from app.core.config import settings
from app.services.mock_stt_service import get_mock_stt_service

logger = logging.getLogger(__name__)


class RealtimeVoiceService:
    """
    Real-time voice service optimized for conversational latency.

    Key features:
    - Streaming LLM responses
    - Streaming TTS via ElevenLabs WebSocket - audio plays as it's generated
    - Minimal conversation history
    
    Uses ElevenLabs for TTS and OpenAI Whisper for STT.
    """

    def __init__(self):
        self.elevenlabs_api_key = settings.ELEVENLABS_API_KEY
        self.elevenlabs_voice_id = settings.ELEVENLABS_VOICE_ID
        self.elevenlabs_model = settings.ELEVENLABS_MODEL
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.openrouter_client = AsyncOpenAI(
            base_url=settings.OPENROUTER_BASE_URL,
            api_key=settings.OPENROUTER_API_KEY,
        )
        self.llm_model = settings.OPENROUTER_MODEL
        
        # ElevenLabs WebSocket URL for streaming TTS
        self.elevenlabs_ws_url = f"wss://api.elevenlabs.io/v1/text-to-speech/{self.elevenlabs_voice_id}/stream-input?model_id={self.elevenlabs_model}&output_format=mp3_44100_128"

    async def transcribe_audio_fast(self, audio_data: bytes, mime_type: str = "audio/webm") -> dict:
        """Fast STT using OpenAI Whisper or Mock STT. Handles various audio formats."""
        # Check if using mock STT for testing
        if settings.USE_MOCK_STT:
            logger.info("Using mock STT service (no API costs)")
            mock_service = get_mock_stt_service(
                use_random=settings.MOCK_STT_RANDOM,
                mode="training"
            )
            return await mock_service.transcribe_async(audio_data)
        
        try:
            # Check if audio is too short
            if len(audio_data) < 100:
                logger.warning(f"Audio too short: {len(audio_data)} bytes")
                return {"transcript": "", "confidence": 0.0, "error": "Audio too short"}
            
            # Detect audio format from magic bytes or use provided mime_type
            file_ext = "webm"  # Default to webm (browser recording format)
            
            # Check magic bytes to detect format
            if audio_data[:4] == b'RIFF':
                file_ext = "wav"
            elif audio_data[:4] == b'\x1aE\xdf\xa3':  # WebM/Matroska magic bytes
                file_ext = "webm"
            elif audio_data[:3] == b'ID3' or audio_data[:2] == b'\xff\xfb':
                file_ext = "mp3"
            elif audio_data[:4] == b'OggS':
                file_ext = "ogg"
            elif audio_data[:4] == b'fLaC':
                file_ext = "flac"
            else:
                # Use mime_type to determine extension
                ext_map = {
                    "audio/wav": "wav",
                    "audio/webm": "webm",
                    "audio/mp3": "mp3",
                    "audio/mpeg": "mp3",
                    "audio/ogg": "ogg",
                    "audio/flac": "flac",
                    "audio/m4a": "m4a",
                    "audio/mp4": "m4a",
                }
                file_ext = ext_map.get(mime_type, "webm")
            
            # Create a file-like object with the correct extension
            audio_buffer = io.BytesIO(audio_data)
            audio_buffer.name = f"audio.{file_ext}"

            logger.info(f"Transcribing {len(audio_data)} bytes of {file_ext} audio")
            
            response = await self.openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_buffer,
                language="en",
                response_format="verbose_json",
            )

            logger.info(f"Transcription result: '{response.text}'")
            
            return {
                "transcript": response.text,
                "confidence": 1.0,  # Whisper doesn't provide confidence scores
            }
        except Exception as e:
            error_str = str(e)
            logger.error(f"STT Error: {error_str}")
            
            # Check for specific error types
            if "insufficient_quota" in error_str or "429" in error_str:
                logger.error("OpenAI API quota exceeded. Please check your billing and API key.")
                logger.error("💡 Tip: Set USE_MOCK_STT=true in .env to test without API costs")
                return {
                    "transcript": "",
                    "confidence": 0.0,
                    "error": "OpenAI API quota exceeded. Please check your billing and API key. Set USE_MOCK_STT=true to test without costs."
                }
            elif "getaddrinfo failed" in error_str or "ConnectError" in error_str:
                logger.error("Network connectivity issue. Cannot reach OpenAI API.")
                return {
                    "transcript": "",
                    "confidence": 0.0,
                    "error": "Network connectivity issue. Cannot reach OpenAI API."
                }
            
            return {"transcript": "", "confidence": 0.0, "error": error_str}

    async def generate_response_stream(
        self,
        query: str,
        mode: str = "training",
        conversation_history: list[dict] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream LLM response token by token."""
        if mode == "training":
            system_prompt = """You are Adam, an expert F&I trainer. Be very concise - this is a voice call.
Keep responses to 1-2 short sentences. Speak naturally."""
        else:
            system_prompt = """You are a car dealership customer in the F&I office talking to a dealer/F&I manager. Be very concise - this is a voice call.
If starting the conversation, express interest in what products or protection plans are available.
Ask about warranties, GAP insurance, or other F&I products. Present objections when pitched.
Give short, natural responses. One concern or question at a time. Never break character."""

        messages = [{"role": "system", "content": system_prompt}]

        if conversation_history:
            messages.extend(conversation_history[-4:])

        messages.append({"role": "user", "content": query})

        stream = await self.openrouter_client.chat.completions.create(
            model=self.llm_model,
            messages=messages,
            temperature=0.7,
            max_tokens=60,  # Very short for voice
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def text_to_speech_sync(self, text: str) -> bytes:
        """Sync TTS using ElevenLabs - fast for short text."""
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.elevenlabs_voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.elevenlabs_api_key,
        }
        
        data = {
            "text": text,
            "model_id": self.elevenlabs_model,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            }
        }
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, json=data, headers=headers)
            response.raise_for_status()
            return response.content

    async def text_to_speech(self, text: str) -> bytes:
        """Async TTS wrapper."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.text_to_speech_sync, text)

    async def text_to_speech_stream(self, text: str) -> AsyncGenerator[bytes, None]:
        """
        Stream TTS using ElevenLabs HTTP streaming endpoint.
        Yields audio chunks as they're generated.
        """
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.elevenlabs_voice_id}/stream"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.elevenlabs_api_key,
        }
        
        data = {
            "text": text,
            "model_id": self.elevenlabs_model,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            }
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("POST", url, json=data, headers=headers) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes(chunk_size=1024):
                    if chunk:
                        yield chunk

    async def stream_tts_websocket(
        self,
        text_generator: AsyncGenerator[str, None],
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream TTS using ElevenLabs WebSocket for lowest latency.
        Takes a text generator (e.g., LLM stream) and yields audio chunks.
        
        This is the fastest option - audio starts playing while text is still being generated.
        """
        try:
            async with websockets.connect(self.elevenlabs_ws_url) as ws:
                # Send initial message with voice settings
                init_message = {
                    "text": " ",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75,
                    },
                    "xi_api_key": self.elevenlabs_api_key,
                }
                await ws.send(json.dumps(init_message))
                
                # Task to receive audio chunks
                audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue()
                
                async def receive_audio():
                    try:
                        async for message in ws:
                            data = json.loads(message)
                            if "audio" in data and data["audio"]:
                                audio_bytes = base64.b64decode(data["audio"])
                                await audio_queue.put(audio_bytes)
                            if data.get("isFinal"):
                                await audio_queue.put(None)
                                break
                    except Exception as e:
                        logger.error(f"WebSocket receive error: {e}")
                        await audio_queue.put(None)
                
                # Start receiving audio in background
                receive_task = asyncio.create_task(receive_audio())
                
                # Send text chunks as they come from LLM
                async for text_chunk in text_generator:
                    if text_chunk:
                        await ws.send(json.dumps({
                            "text": text_chunk,
                            "try_trigger_generation": True,
                        }))
                
                # Signal end of text
                await ws.send(json.dumps({"text": ""}))
                
                # Yield audio chunks as they arrive
                while True:
                    audio_chunk = await audio_queue.get()
                    if audio_chunk is None:
                        break
                    yield audio_chunk
                
                await receive_task
                
        except Exception as e:
            logger.error(f"WebSocket TTS error: {e}")
            raise

    async def process_voice_streaming(
        self,
        audio_data: bytes,
        mode: str = "training",
        conversation_history: list[dict] | None = None,
        use_websocket_tts: bool = True,
    ) -> AsyncGenerator[dict, None]:
        """
        Stream the full pipeline - yields audio chunks as they're generated.

        Yields:
        - {"type": "transcript", "text": "user said this"}
        - {"type": "audio_chunk", "data": base64_audio} - streaming audio chunks
        - {"type": "audio", "data": base64_audio} - complete audio (fallback mode)
        - {"type": "done", "text": "full response"}
        
        Args:
            use_websocket_tts: If True, uses ElevenLabs WebSocket for lowest latency.
                              Audio starts playing while LLM is still generating text.
        """
        # 1. STT (OpenAI Whisper auto-detects audio format)
        stt_result = await self.transcribe_audio_fast(audio_data)
        transcript = stt_result["transcript"]
        
        # Check for STT error
        if stt_result.get("error"):
            yield {"type": "error", "message": f"Speech recognition failed: {stt_result['error']}"}
            return

        yield {"type": "transcript", "text": transcript}

        if not transcript:
            fallback = "Sorry, I didn't catch that."
            audio = await self.text_to_speech(fallback)
            yield {"type": "audio", "data": base64.b64encode(audio).decode()}
            yield {"type": "done", "text": fallback}
            return

        if use_websocket_tts:
            # Use WebSocket streaming for lowest latency
            # Audio starts playing while LLM is still generating!
            full_response = ""
            
            async def text_with_tracking():
                nonlocal full_response
                async for token in self.generate_response_stream(
                    query=transcript,
                    mode=mode,
                    conversation_history=conversation_history,
                ):
                    full_response += token
                    yield token
            
            try:
                async for audio_chunk in self.stream_tts_websocket(text_with_tracking()):
                    yield {"type": "audio_chunk", "data": base64.b64encode(audio_chunk).decode()}
                
                yield {"type": "done", "text": full_response}
            except Exception as e:
                logger.error(f"WebSocket TTS failed, falling back to sentence-by-sentence: {e}")
                # Fall through to sentence-by-sentence mode
                use_websocket_tts = False
        
        if not use_websocket_tts:
            # Fallback: Stream LLM and TTS sentence by sentence
            full_response = ""
            sentence_buffer = ""
            sentence_endings = {".", "!", "?", ","}

            async for token in self.generate_response_stream(
                query=transcript,
                mode=mode,
                conversation_history=conversation_history,
            ):
                full_response += token
                sentence_buffer += token

                # Check if we have a complete sentence
                if any(sentence_buffer.rstrip().endswith(end) for end in sentence_endings):
                    if len(sentence_buffer.strip()) > 5:  # Min length
                        audio = await self.text_to_speech(sentence_buffer.strip())
                        yield {"type": "audio", "data": base64.b64encode(audio).decode()}
                        sentence_buffer = ""

            # Send any remaining text
            if sentence_buffer.strip():
                audio = await self.text_to_speech(sentence_buffer.strip())
                yield {"type": "audio", "data": base64.b64encode(audio).decode()}

            yield {"type": "done", "text": full_response}

    async def process_voice_fast(
        self,
        audio_data: bytes,
        mode: str = "training",
        context: str = "",
        conversation_history: list[dict] | None = None,
        mime_type: str = "audio/webm",
    ) -> dict:
        """Non-streaming version for simple endpoint."""
        stt_result = await self.transcribe_audio_fast(audio_data, mime_type=mime_type)
        transcript = stt_result["transcript"]
        confidence = stt_result.get("confidence", 0.0)
        error = stt_result.get("error")

        if not transcript:
            # Check if there's a specific error
            if error:
                if "quota" in error.lower() or "429" in error:
                    fallback = "API quota exceeded. Please check your OpenAI billing."
                elif "network" in error.lower() or "connect" in error.lower():
                    fallback = "Network error. Please check your internet connection."
                elif "too short" in error.lower():
                    fallback = "Audio was too short. Please speak longer."
                else:
                    fallback = f"Error: {error}"
            else:
                fallback = "I didn't catch that. Please speak again."
            
            logger.warning(f"STT failed with error: {error}")
            return {
                "transcript": "",
                "response": fallback,
                "audio": await self.text_to_speech(fallback),
                "confidence": 0.0,
            }

        # Generate response
        response_text = ""
        async for chunk in self.generate_response_stream(
            query=transcript,
            mode=mode,
            conversation_history=conversation_history,
        ):
            response_text += chunk

        audio = await self.text_to_speech(response_text)

        return {
            "transcript": transcript,
            "response": response_text,
            "audio": audio,
            "confidence": confidence,
        }


_realtime_service: RealtimeVoiceService | None = None


def get_realtime_voice_service() -> RealtimeVoiceService:
    global _realtime_service
    if _realtime_service is None:
        _realtime_service = RealtimeVoiceService()
    return _realtime_service
