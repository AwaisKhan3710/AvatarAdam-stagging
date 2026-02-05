"""Voice Service using ElevenLabs for TTS and OpenAI Whisper for STT."""

import asyncio
import base64
import io
from typing import Any, Callable

import httpx
from openai import AsyncOpenAI

from app.core.config import settings


class VoiceService:
    """Service for voice operations using ElevenLabs (TTS) and OpenAI Whisper (STT)."""

    def __init__(self):
        """Initialize ElevenLabs and OpenAI clients."""
        self.elevenlabs_api_key = settings.ELEVENLABS_API_KEY
        self.elevenlabs_voice_id = settings.ELEVENLABS_VOICE_ID
        self.elevenlabs_model = settings.ELEVENLABS_MODEL
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def transcribe_audio(
        self,
        audio_data: bytes,
        mime_type: str = "audio/wav",
        language: str = "en",
    ) -> dict:
        """
        Transcribe audio to text using OpenAI Whisper.

        Args:
            audio_data: Audio bytes
            mime_type: Audio MIME type
            language: Language code

        Returns:
            Transcription result with text and metadata
        """
        # Determine file extension from mime type
        ext_map = {
            "audio/wav": "wav",
            "audio/webm": "webm",
            "audio/mp3": "mp3",
            "audio/mpeg": "mp3",
            "audio/ogg": "ogg",
            "audio/flac": "flac",
            "audio/m4a": "m4a",
        }
        ext = ext_map.get(mime_type, "wav")
        
        # Create a file-like object for the API
        audio_file = io.BytesIO(audio_data)
        audio_file.name = f"audio.{ext}"

        try:
            response = await self.openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language,
                response_format="verbose_json",
            )

            return {
                "transcript": response.text,
                "confidence": 1.0,  # Whisper doesn't provide confidence scores
                "words": [],
                "language": language,
            }
        except Exception as e:
            return {
                "transcript": "",
                "confidence": 0.0,
                "words": [],
                "language": language,
                "error": str(e),
            }

    def _text_to_speech_sync(self, text: str, voice_id: str | None = None) -> bytes:
        """Sync TTS using ElevenLabs - runs in thread pool to avoid blocking."""
        import httpx
        
        voice = voice_id or self.elevenlabs_voice_id
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice}"
        
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

    async def text_to_speech(
        self,
        text: str,
        voice_id: str | None = None,
    ) -> bytes:
        """
        Convert text to speech using ElevenLabs.

        Args:
            text: Text to convert
            voice_id: Optional voice ID override

        Returns:
            Audio bytes (MP3 format)
        """
        # Run sync TTS in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            lambda: self._text_to_speech_sync(text, voice_id)
        )

    async def text_to_speech_base64(
        self,
        text: str,
        voice_id: str | None = None,
    ) -> str:
        """
        Convert text to speech and return as base64.

        Args:
            text: Text to convert
            voice_id: Optional voice ID override

        Returns:
            Base64-encoded audio string
        """
        audio_data = await self.text_to_speech(text, voice_id)
        return base64.b64encode(audio_data).decode("utf-8")


class VoiceChatSession:
    """Manages a voice chat session with STT/TTS."""

    def __init__(
        self,
        voice_service: VoiceService,
        llm_callback: Callable,
        rag_callback: Callable | None = None,
    ):
        """
        Initialize voice chat session.

        Args:
            voice_service: VoiceService instance
            llm_callback: Async function to call LLM with text
            rag_callback: Optional async function to get RAG context
        """
        self.voice_service = voice_service
        self.llm_callback = llm_callback
        self.rag_callback = rag_callback
        self.conversation_history: list[dict] = []

    async def process_audio(
        self,
        audio_data: bytes,
        mode: str = "training",
    ) -> dict:
        """
        Process audio input and generate voice response.

        Args:
            audio_data: Audio bytes from user
            mode: "training" or "roleplay"

        Returns:
            Dict with transcript, response text, and audio
        """
        # 1. Transcribe audio to text
        transcription = await self.voice_service.transcribe_audio(audio_data)
        user_text = transcription["transcript"]

        if not user_text:
            return {
                "user_transcript": "",
                "response_text": "I didn't catch that. Could you please repeat?",
                "response_audio": await self.voice_service.text_to_speech_base64(
                    "I didn't catch that. Could you please repeat?"
                ),
            }

        # 2. Get RAG context if available (both modes can use RAG)
        context = ""
        if self.rag_callback:
            try:
                context = await self.rag_callback(user_text, mode)
            except TypeError:
                # Fallback for callbacks that don't accept mode parameter
                context = await self.rag_callback(user_text)

        # 3. Generate LLM response
        response_text = await self.llm_callback(
            user_text,
            context=context,
            mode=mode,
            conversation_history=self.conversation_history,
        )

        # 4. Update conversation history
        self.conversation_history.append({"role": "user", "content": user_text})
        self.conversation_history.append(
            {"role": "assistant", "content": response_text}
        )

        # Keep history manageable (last 10 exchanges)
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]

        # 5. Convert response to speech
        response_audio = await self.voice_service.text_to_speech_base64(response_text)

        return {
            "user_transcript": user_text,
            "response_text": response_text,
            "response_audio": response_audio,
            "confidence": transcription["confidence"],
        }

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []


# Singleton instance
_voice_service: VoiceService | None = None


def get_voice_service() -> VoiceService:
    """Get or create Voice service instance."""
    global _voice_service
    if _voice_service is None:
        _voice_service = VoiceService()
    return _voice_service
