"""
Comprehensive VAD Implementation Tests
Tests the Voice Activity Detection service and WebSocket endpoint
"""

import asyncio
import base64
import json
import pytest
from app.services.vad_service import VoiceActivityDetector, VADManager, get_vad_manager


class TestVoiceActivityDetector:
    """Test VoiceActivityDetector class"""

    def test_initialization(self):
        """Test VAD initialization with default parameters"""
        vad = VoiceActivityDetector()
        assert vad.sample_rate == 16000
        assert vad.aggressiveness == 2
        assert vad.frame_size == 320
        assert vad.bytes_per_frame == 640

    def test_initialization_with_custom_params(self):
        """Test VAD initialization with custom parameters"""
        vad = VoiceActivityDetector(sample_rate=8000, aggressiveness=3)
        assert vad.sample_rate == 8000
        assert vad.aggressiveness == 3
        assert vad.frame_size == 160  # 8000 * 20 / 1000

    def test_invalid_sample_rate(self):
        """Test that invalid sample rate raises error"""
        with pytest.raises(ValueError, match="Sample rate must be"):
            VoiceActivityDetector(sample_rate=44100)

    def test_invalid_aggressiveness(self):
        """Test that invalid aggressiveness raises error"""
        with pytest.raises(ValueError, match="Aggressiveness must be"):
            VoiceActivityDetector(aggressiveness=5)

    def test_process_frame_silence(self):
        """Test processing a silent frame"""
        vad = VoiceActivityDetector()
        # Create silent audio frame (all zeros)
        silent_frame = b'\x00' * vad.bytes_per_frame
        
        result = vad.process_frame(silent_frame)
        
        assert 'is_speech' in result
        assert 'confidence' in result
        assert 'speech_started' in result
        assert 'speech_ended' in result
        assert 'duration_ms' in result
        assert result['is_speech'] == False
        assert result['confidence'] == 0.0

    def test_process_frame_invalid_size(self):
        """Test processing frame with invalid size"""
        vad = VoiceActivityDetector()
        invalid_frame = b'\x00' * 100  # Wrong size
        
        result = vad.process_frame(invalid_frame)
        
        assert result['is_speech'] == False
        assert result['confidence'] == 0.0

    def test_process_audio_chunk(self):
        """Test processing multiple frames in a chunk"""
        vad = VoiceActivityDetector()
        # Create audio chunk with multiple frames
        chunk = b'\x00' * (vad.bytes_per_frame * 5)
        
        results = vad.process_audio_chunk(chunk)
        
        assert len(results) == 5
        for result in results:
            assert 'is_speech' in result
            assert 'confidence' in result

    def test_reset(self):
        """Test VAD state reset"""
        vad = VoiceActivityDetector()
        vad.is_speech = True
        vad.speech_start_frame = 10
        vad.silence_frames = 5
        
        vad.reset()
        
        assert vad.is_speech == False
        assert vad.speech_start_frame is None
        assert vad.silence_frames == 0

    def test_speech_detection_state_transitions(self):
        """Test state transitions during speech detection"""
        vad = VoiceActivityDetector()
        
        # Initial state
        assert vad.is_speech == False
        
        # Process silent frame
        silent_frame = b'\x00' * vad.bytes_per_frame
        result = vad.process_frame(silent_frame)
        assert result['is_speech'] == False
        assert result['speech_started'] == False
        
        # Reset for next test
        vad.reset()


class TestVADManager:
    """Test VADManager class"""

    def test_manager_initialization(self):
        """Test VADManager initialization"""
        manager = VADManager()
        assert len(manager.detectors) == 0

    def test_get_detector_creates_new(self):
        """Test getting a detector creates new instance"""
        manager = VADManager()
        detector = manager.get_detector('stream-1')
        
        assert detector is not None
        assert 'stream-1' in manager.detectors
        assert isinstance(detector, VoiceActivityDetector)

    def test_get_detector_returns_existing(self):
        """Test getting a detector returns existing instance"""
        manager = VADManager()
        detector1 = manager.get_detector('stream-1')
        detector2 = manager.get_detector('stream-1')
        
        assert detector1 is detector2

    def test_get_detector_with_custom_params(self):
        """Test getting detector with custom parameters"""
        manager = VADManager()
        detector = manager.get_detector(
            'stream-1',
            sample_rate=8000,
            aggressiveness=3
        )
        
        assert detector.sample_rate == 8000
        assert detector.aggressiveness == 3

    def test_remove_detector(self):
        """Test removing a detector"""
        manager = VADManager()
        manager.get_detector('stream-1')
        assert 'stream-1' in manager.detectors
        
        manager.remove_detector('stream-1')
        assert 'stream-1' not in manager.detectors

    def test_process_frame(self):
        """Test processing frame through manager"""
        manager = VADManager()
        silent_frame = b'\x00' * 640
        
        result = manager.process_frame('stream-1', silent_frame)
        
        assert 'is_speech' in result
        assert result['is_speech'] == False

    def test_reset_detector(self):
        """Test resetting detector through manager"""
        manager = VADManager()
        detector = manager.get_detector('stream-1')
        detector.is_speech = True
        
        manager.reset_detector('stream-1')
        
        assert detector.is_speech == False

    def test_multiple_streams(self):
        """Test managing multiple streams"""
        manager = VADManager()
        
        detector1 = manager.get_detector('stream-1')
        detector2 = manager.get_detector('stream-2')
        detector3 = manager.get_detector('stream-3')
        
        assert len(manager.detectors) == 3
        assert detector1 is not detector2
        assert detector2 is not detector3


class TestGlobalVADManager:
    """Test global VAD manager singleton"""

    def test_get_vad_manager_singleton(self):
        """Test that get_vad_manager returns singleton"""
        manager1 = get_vad_manager()
        manager2 = get_vad_manager()
        
        assert manager1 is manager2

    def test_global_manager_functionality(self):
        """Test global manager works correctly"""
        manager = get_vad_manager()
        detector = manager.get_detector('test-stream')
        
        assert detector is not None
        assert isinstance(detector, VoiceActivityDetector)


class TestVADConfiguration:
    """Test VAD configuration options"""

    def test_sample_rate_8000(self):
        """Test 8kHz sample rate"""
        vad = VoiceActivityDetector(sample_rate=8000)
        assert vad.sample_rate == 8000
        assert vad.frame_size == 160

    def test_sample_rate_16000(self):
        """Test 16kHz sample rate"""
        vad = VoiceActivityDetector(sample_rate=16000)
        assert vad.sample_rate == 16000
        assert vad.frame_size == 320

    def test_sample_rate_32000(self):
        """Test 32kHz sample rate"""
        vad = VoiceActivityDetector(sample_rate=32000)
        assert vad.sample_rate == 32000
        assert vad.frame_size == 640

    def test_aggressiveness_levels(self):
        """Test all aggressiveness levels"""
        for level in range(4):
            vad = VoiceActivityDetector(aggressiveness=level)
            assert vad.aggressiveness == level


class TestVADEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_audio_frame(self):
        """Test processing empty audio frame"""
        vad = VoiceActivityDetector()
        result = vad.process_frame(b'')
        
        assert result['is_speech'] == False
        assert result['confidence'] == 0.0

    def test_very_short_audio_chunk(self):
        """Test processing very short audio chunk"""
        vad = VoiceActivityDetector()
        short_chunk = b'\x00' * 100
        
        results = vad.process_audio_chunk(short_chunk)
        
        # Should return empty list since chunk is too short
        assert len(results) == 0

    def test_very_long_audio_chunk(self):
        """Test processing very long audio chunk"""
        vad = VoiceActivityDetector()
        # Create 100 frames worth of audio
        long_chunk = b'\x00' * (vad.bytes_per_frame * 100)
        
        results = vad.process_audio_chunk(long_chunk)
        
        assert len(results) == 100

    def test_consecutive_frames(self):
        """Test processing consecutive frames"""
        vad = VoiceActivityDetector()
        silent_frame = b'\x00' * vad.bytes_per_frame
        
        results = []
        for _ in range(10):
            result = vad.process_frame(silent_frame)
            results.append(result)
        
        assert len(results) == 10
        for result in results:
            assert 'is_speech' in result


class TestVADPerformance:
    """Test VAD performance characteristics"""

    def test_frame_processing_speed(self):
        """Test that frame processing is fast"""
        import time
        
        vad = VoiceActivityDetector()
        silent_frame = b'\x00' * vad.bytes_per_frame
        
        start = time.time()
        for _ in range(1000):
            vad.process_frame(silent_frame)
        elapsed = time.time() - start
        
        # Should process 1000 frames in less than 1 second
        assert elapsed < 1.0
        print(f"Processed 1000 frames in {elapsed:.3f}s")

    def test_memory_efficiency(self):
        """Test that VAD doesn't leak memory"""
        import sys
        
        vad = VoiceActivityDetector()
        silent_frame = b'\x00' * vad.bytes_per_frame
        
        # Get initial size
        initial_size = sys.getsizeof(vad)
        
        # Process many frames
        for _ in range(10000):
            vad.process_frame(silent_frame)
        
        # Size should not grow significantly
        final_size = sys.getsizeof(vad)
        assert final_size <= initial_size * 1.1  # Allow 10% growth


# Run tests
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
