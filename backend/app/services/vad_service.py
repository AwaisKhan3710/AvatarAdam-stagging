"""Voice Activity Detection (VAD) service using WebRTC VAD."""

import logging
from typing import Optional

try:
    import webrtcvad
except ImportError:
    webrtcvad = None  # type: ignore

logger = logging.getLogger(__name__)


class VoiceActivityDetector:
    """
    Real-time Voice Activity Detection using WebRTC VAD.
    
    Features:
    - Detects speech vs silence in real-time
    - Configurable aggressiveness (0-3, higher = more aggressive)
    - Efficient processing of audio frames
    - Supports 8kHz, 16kHz, and 32kHz sample rates
    """

    def __init__(self, sample_rate: int = 16000, aggressiveness: int = 2):
        """
        Initialize VAD detector.
        
        Args:
            sample_rate: Audio sample rate (8000, 16000, or 32000 Hz)
            aggressiveness: VAD aggressiveness (0-3)
                - 0: Most permissive (detects more speech, more false positives)
                - 3: Most aggressive (detects less speech, fewer false positives)
        """
        if webrtcvad is None:
            raise ImportError("webrtcvad is not installed. Install it with: pip install webrtcvad>=4.3.1")
        
        if sample_rate not in [8000, 16000, 32000]:
            raise ValueError(f"Sample rate must be 8000, 16000, or 32000, got {sample_rate}")
        if not 0 <= aggressiveness <= 3:
            raise ValueError(f"Aggressiveness must be 0-3, got {aggressiveness}")
        
        self.sample_rate = sample_rate
        self.aggressiveness = aggressiveness
        self.vad = webrtcvad.Vad(aggressiveness)
        
        # Frame size in milliseconds (10, 20, or 30)
        self.frame_duration_ms = 20
        self.frame_size = int(sample_rate * self.frame_duration_ms / 1000)
        self.bytes_per_frame = self.frame_size * 2  # 16-bit audio
        
        # State tracking
        self.is_speech = False
        self.speech_start_frame = None
        self.silence_frames = 0
        self.silence_threshold = 10  # Frames of silence before considering speech ended
        
        logger.info(
            f"VAD initialized: sample_rate={sample_rate}Hz, "
            f"aggressiveness={aggressiveness}, frame_size={self.frame_size}"
        )

    def process_frame(self, audio_bytes: bytes) -> dict:
        """
        Process a single audio frame and detect voice activity.
        
        Args:
            audio_bytes: Raw audio bytes (16-bit PCM)
            
        Returns:
            {
                "is_speech": bool,
                "confidence": float (0.0-1.0),
                "speech_started": bool,
                "speech_ended": bool,
                "duration_ms": int
            }
        """
        if len(audio_bytes) != self.bytes_per_frame:
            logger.warning(
                f"Expected {self.bytes_per_frame} bytes, got {len(audio_bytes)}"
            )
            return {
                "is_speech": False,
                "confidence": 0.0,
                "speech_started": False,
                "speech_ended": False,
                "duration_ms": 0,
            }

        try:
            is_speech = self.vad.is_speech(audio_bytes, self.sample_rate)
        except Exception as e:
            logger.error(f"VAD processing error: {e}")
            return {
                "is_speech": False,
                "confidence": 0.0,
                "speech_started": False,
                "speech_ended": False,
                "duration_ms": 0,
            }

        speech_started = False
        speech_ended = False
        duration_ms = 0

        if is_speech:
            self.silence_frames = 0
            
            if not self.is_speech:
                # Speech just started
                self.is_speech = True
                self.speech_start_frame = 0
                speech_started = True
                logger.debug("Speech detected - starting")
        else:
            # Silence detected
            self.silence_frames += 1
            
            if self.is_speech and self.silence_frames >= self.silence_threshold:
                # Speech just ended
                self.is_speech = False
                speech_ended = True
                logger.debug("Speech ended - silence threshold reached")

        # Calculate speech duration if currently speaking
        if self.is_speech and self.speech_start_frame is not None:
            duration_ms = (self.speech_start_frame + 1) * self.frame_duration_ms
            self.speech_start_frame += 1

        return {
            "is_speech": self.is_speech,
            "confidence": 1.0 if is_speech else 0.0,
            "speech_started": speech_started,
            "speech_ended": speech_ended,
            "duration_ms": duration_ms,
        }

    def process_audio_chunk(self, audio_bytes: bytes) -> list[dict]:
        """
        Process a chunk of audio that may contain multiple frames.
        
        Args:
            audio_bytes: Raw audio bytes (16-bit PCM)
            
        Returns:
            List of frame results
        """
        results = []
        offset = 0
        
        while offset + self.bytes_per_frame <= len(audio_bytes):
            frame = audio_bytes[offset : offset + self.bytes_per_frame]
            result = self.process_frame(frame)
            results.append(result)
            offset += self.bytes_per_frame
        
        return results

    def reset(self):
        """Reset VAD state."""
        self.is_speech = False
        self.speech_start_frame = None
        self.silence_frames = 0
        logger.debug("VAD state reset")


class VADManager:
    """Manages multiple VAD instances for different audio streams."""

    def __init__(self):
        self.detectors: dict[str, VoiceActivityDetector] = {}

    def get_detector(
        self,
        stream_id: str,
        sample_rate: int = 16000,
        aggressiveness: int = 2,
    ) -> VoiceActivityDetector:
        """Get or create a VAD detector for a stream."""
        if stream_id not in self.detectors:
            self.detectors[stream_id] = VoiceActivityDetector(
                sample_rate=sample_rate,
                aggressiveness=aggressiveness,
            )
        return self.detectors[stream_id]

    def remove_detector(self, stream_id: str):
        """Remove a VAD detector."""
        if stream_id in self.detectors:
            del self.detectors[stream_id]
            logger.debug(f"Removed VAD detector for stream {stream_id}")

    def process_frame(self, stream_id: str, audio_bytes: bytes) -> dict:
        """Process a frame for a specific stream."""
        detector = self.get_detector(stream_id)
        return detector.process_frame(audio_bytes)

    def reset_detector(self, stream_id: str):
        """Reset a specific detector."""
        if stream_id in self.detectors:
            self.detectors[stream_id].reset()


# Global VAD manager instance
_vad_manager: Optional[VADManager] = None


def get_vad_manager() -> VADManager:
    """Get the global VAD manager instance."""
    global _vad_manager
    if _vad_manager is None:
        _vad_manager = VADManager()
    return _vad_manager
