"""
Mock STT Service for testing without OpenAI API costs.

This service simulates Whisper transcription for development and testing.
Use this when you want to test the voice chat without consuming OpenAI API quota.
"""

import logging
import random
from typing import Optional

logger = logging.getLogger(__name__)


class MockSTTService:
    """Mock Speech-to-Text service for testing."""

    # Sample test phrases for different scenarios
    TRAINING_PHRASES = [
        "Tell me about the warranty options",
        "What protection plans do you offer",
        "How much does the extended warranty cost",
        "Can you explain the gap insurance",
        "What's included in the maintenance plan",
        "Do you have any special offers today",
        "How long is the warranty valid",
        "What happens if I need to make a claim",
        "Are there any exclusions I should know about",
        "Can I upgrade my coverage later",
    ]

    ROLEPLAY_PHRASES = [
        "I'm interested in learning more",
        "That sounds good, tell me more",
        "What's the price for that",
        "How long does it take",
        "Is there a discount available",
        "Can I think about it",
        "What if I have questions later",
        "Do you offer financing options",
        "What's your return policy",
        "Can I get that in writing",
    ]

    def __init__(self, use_random: bool = True, mode: str = "training"):
        """
        Initialize mock STT service.

        Args:
            use_random: If True, returns random phrases. If False, cycles through phrases.
            mode: "training" or "roleplay" to determine which phrases to use.
        """
        self.use_random = use_random
        self.mode = mode
        self.phrase_index = 0
        logger.info(f"MockSTTService initialized (mode={mode}, random={use_random})")

    def set_mode(self, mode: str):
        """Set the mode for phrase selection."""
        self.mode = mode
        self.phrase_index = 0

    def transcribe(self, audio_data: bytes) -> dict:
        """
        Mock transcription of audio data.

        Args:
            audio_data: Raw audio bytes (ignored in mock)

        Returns:
            Dictionary with transcript and confidence
        """
        phrases = (
            self.TRAINING_PHRASES
            if self.mode == "training"
            else self.ROLEPLAY_PHRASES
        )

        if self.use_random:
            transcript = random.choice(phrases)
        else:
            transcript = phrases[self.phrase_index % len(phrases)]
            self.phrase_index += 1

        logger.info(f"Mock transcription: '{transcript}'")

        return {
            "transcript": transcript,
            "confidence": random.uniform(0.85, 0.99),  # Simulate confidence
        }

    async def transcribe_async(self, audio_data: bytes) -> dict:
        """Async version of transcribe."""
        return self.transcribe(audio_data)


# Global mock service instance
_mock_stt_service: Optional[MockSTTService] = None


def get_mock_stt_service(
    use_random: bool = True, mode: str = "training"
) -> MockSTTService:
    """Get or create the global mock STT service."""
    global _mock_stt_service
    if _mock_stt_service is None:
        _mock_stt_service = MockSTTService(use_random=use_random, mode=mode)
    return _mock_stt_service


def set_mock_stt_mode(mode: str):
    """Set the mode for the mock STT service."""
    service = get_mock_stt_service()
    service.set_mode(mode)
