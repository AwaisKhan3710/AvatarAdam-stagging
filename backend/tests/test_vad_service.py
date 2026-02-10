"""Tests for VAD Service"""

import pytest
from app.services.vad_service import VoiceActivityDetector, VADManager, get_vad_manager


class TestVoiceActivityDetector:
    """Test VoiceActivityDetector class"""

    def test_initialization_default(self):
        """Test VAD initialization with default parameters"""
        vad = VoiceActivityDetector()
        assert vad.sample_rate == 16000
        assert vad.aggressiveness == 2
        assert vad.frame_duration_ms == 20
        assert vad.frame_size == 320

    def test_initialization_custom_sample_rate(self):
        """Test VAD initialization with custom sample rate"""
        vad = VoiceActivityDetector(sample_rate=8000)
        assert vad.sample_rate == 8000
        assert vad.frame_size == 160  # 8000 * 20 / 1000

    def test_initialization_invalid_sample_rate(self):
        """Test VAD initialization with invalid sample rate"""
        with pytest.raises(ValueError, match="Sample rate must be"):
            VoiceActivityDetector(sample_rate=44100)

    def test_initialization_invalid_aggressiveness(self):
        """Test VAD initialization with invalid aggressiveness"""
        with pytest.raises(ValueError, match="Aggressiveness must be"):
            VoiceActivityDetector(aggressiveness=5)

    def test_process_frame_silence(self):
        """Test processing a silent frame"""
        vad = VoiceActivityDetector()
        # Create silent frame (all zeros)
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
        # Create chunk with multiple frames
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

    def test_aggressiveness_levels(self):
        """Test different aggressiveness levels"""
        for aggressiveness in range(4):
            vad = VoiceActivityDetector(aggressiveness=aggressiveness)
            assert vad.aggressiveness == aggressiveness


class TestVADManager:
    """Test VADManager class"""

    def test_get_detector_creates_new(self):
        """Test getting a detector creates new instance"""
        manager = VADManager()
        detector = manager.get_detector('stream1')
        
        assert detector is not None
        assert 'stream1' in manager.detectors

    def test_get_detector_returns_existing(self):
        """Test getting a detector returns existing instance"""
        manager = VADManager()
        detector1 = manager.get_detector('stream1')
        detector2 = manager.get_detector('stream1')
        
        assert detector1 is detector2

    def test_remove_detector(self):
        """Test removing a detector"""
        manager = VADManager()
        manager.get_detector('stream1')
        assert 'stream1' in manager.detectors
        
        manager.remove_detector('stream1')
        assert 'stream1' not in manager.detectors

    def test_process_frame(self):
        """Test processing frame through manager"""
        manager = VADManager()
        silent_frame = b'\x00' * 320
        result = manager.process_frame('stream1', silent_frame)
        
        assert 'is_speech' in result
        assert result['is_speech'] == False

    def test_reset_detector(self):
        """Test resetting detector through manager"""
        manager = VADManager()
        detector = manager.get_detector('stream1')
        detector.is_speech = True
        
        manager.reset_detector('stream1')
        assert detector.is_speech == False

    def test_multiple_streams(self):
        """Test managing multiple streams"""
        manager = VADManager()
        
        detector1 = manager.get_detector('stream1')
        detector2 = manager.get_detector('stream2')
        
        assert detector1 is not detector2
        assert len(manager.detectors) == 2


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
        detector = manager.get_detector('test_stream')
        
        assert detector is not None
        assert 'test_stream' in manager.detectors


class TestVADIntegration:
    """Integration tests for VAD"""

    def test_speech_detection_flow(self):
        """Test complete speech detection flow"""
        vad = VoiceActivityDetector()
        
        # Process multiple silent frames
        for _ in range(5):
            silent_frame = b'\x00' * vad.bytes_per_frame
            result = vad.process_frame(silent_frame)
            assert result['is_speech'] == False
        
        # Reset for next test
        vad.reset()
        assert vad.is_speech == False

    def test_different_sample_rates(self):
        """Test VAD with different sample rates"""
        for sample_rate in [8000, 16000, 32000]:
            vad = VoiceActivityDetector(sample_rate=sample_rate)
            frame = b'\x00' * vad.bytes_per_frame
            result = vad.process_frame(frame)
            assert 'is_speech' in result

    def test_concurrent_streams(self):
        """Test managing concurrent streams"""
        manager = VADManager()
        
        # Create multiple streams
        streams = ['stream1', 'stream2', 'stream3']
        detectors = [manager.get_detector(s) for s in streams]
        
        # Process frames for each stream
        for detector in detectors:
            frame = b'\x00' * detector.bytes_per_frame
            result = detector.process_frame(frame)
            assert 'is_speech' in result
        
        # Verify all streams are independent
        assert len(manager.detectors) == 3


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
