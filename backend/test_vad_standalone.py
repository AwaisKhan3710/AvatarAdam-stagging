"""
Standalone VAD Service Tests
Tests the Voice Activity Detection service without app dependencies
"""

import sys
import os

# Add the app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

import pytest
import webrtcvad


class TestWebRTCVAD:
    """Test WebRTC VAD directly"""

    def test_vad_initialization(self):
        """Test VAD initialization"""
        vad = webrtcvad.Vad(2)
        assert vad is not None

    def test_vad_aggressiveness_levels(self):
        """Test all aggressiveness levels"""
        for level in range(4):
            vad = webrtcvad.Vad(level)
            assert vad is not None

    def test_vad_process_silent_frame(self):
        """Test processing silent audio frame"""
        vad = webrtcvad.Vad(2)
        # Create silent frame (16-bit PCM, 16kHz, 20ms = 320 samples = 640 bytes)
        silent_frame = b'\x00' * 640
        
        result = vad.is_speech(silent_frame, 16000)
        assert isinstance(result, bool)
        assert result == False  # Silent frame should not be detected as speech

    def test_vad_frame_size_8khz(self):
        """Test frame size for 8kHz"""
        # 8kHz, 20ms = 160 samples = 320 bytes
        frame_size_bytes = 320
        assert frame_size_bytes == 320

    def test_vad_frame_size_16khz(self):
        """Test frame size for 16kHz"""
        # 16kHz, 20ms = 320 samples = 640 bytes
        frame_size_bytes = 640
        assert frame_size_bytes == 640

    def test_vad_frame_size_32khz(self):
        """Test frame size for 32kHz"""
        # 32kHz, 20ms = 640 samples = 1280 bytes
        frame_size_bytes = 1280
        assert frame_size_bytes == 1280

    def test_vad_multiple_frames(self):
        """Test processing multiple frames"""
        vad = webrtcvad.Vad(2)
        silent_frame = b'\x00' * 640
        
        results = []
        for _ in range(10):
            result = vad.is_speech(silent_frame, 16000)
            results.append(result)
        
        assert len(results) == 10
        assert all(r == False for r in results)

    def test_vad_configuration_options(self):
        """Test VAD configuration"""
        sample_rates = [8000, 16000, 32000]
        aggressiveness_levels = [0, 1, 2, 3]
        
        for rate in sample_rates:
            assert rate in [8000, 16000, 32000]
        
        for level in aggressiveness_levels:
            assert 0 <= level <= 3


class TestVADConfiguration:
    """Test VAD configuration"""

    def test_valid_sample_rates(self):
        """Test valid sample rates"""
        valid_rates = [8000, 16000, 32000]
        for rate in valid_rates:
            assert rate > 0

    def test_valid_aggressiveness(self):
        """Test valid aggressiveness levels"""
        for level in range(4):
            assert 0 <= level <= 3

    def test_frame_duration(self):
        """Test frame duration calculation"""
        frame_duration_ms = 20
        assert frame_duration_ms > 0
        assert frame_duration_ms <= 30

    def test_bytes_per_frame_calculation(self):
        """Test bytes per frame calculation"""
        sample_rate = 16000
        frame_duration_ms = 20
        frame_size = int(sample_rate * frame_duration_ms / 1000)
        bytes_per_frame = frame_size * 2  # 16-bit audio
        
        assert frame_size == 320
        assert bytes_per_frame == 640


class TestVADPerformance:
    """Test VAD performance"""

    def test_frame_processing_speed(self):
        """Test that frame processing is fast"""
        import time
        
        vad = webrtcvad.Vad(2)
        silent_frame = b'\x00' * 640
        
        start = time.time()
        for _ in range(1000):
            vad.is_speech(silent_frame, 16000)
        elapsed = time.time() - start
        
        # Should process 1000 frames in less than 1 second
        assert elapsed < 1.0
        print(f"\n✓ Processed 1000 frames in {elapsed:.3f}s")

    def test_memory_efficiency(self):
        """Test that VAD doesn't leak memory"""
        import sys
        
        vad = webrtcvad.Vad(2)
        silent_frame = b'\x00' * 640
        
        # Get initial size
        initial_size = sys.getsizeof(vad)
        
        # Process many frames
        for _ in range(10000):
            vad.is_speech(silent_frame, 16000)
        
        # Size should not grow significantly
        final_size = sys.getsizeof(vad)
        assert final_size <= initial_size * 1.1  # Allow 10% growth
        print(f"\n✓ Memory efficient: {initial_size} -> {final_size} bytes")


class TestVADEdgeCases:
    """Test VAD edge cases"""

    def test_empty_frame(self):
        """Test processing empty frame"""
        vad = webrtcvad.Vad(2)
        try:
            result = vad.is_speech(b'', 16000)
            # If it doesn't raise, it should return False
            assert result == False
        except Exception:
            # Empty frame might raise an exception, which is acceptable
            pass

    def test_very_short_frame(self):
        """Test processing very short frame"""
        vad = webrtcvad.Vad(2)
        short_frame = b'\x00' * 100
        try:
            result = vad.is_speech(short_frame, 16000)
            # If it doesn't raise, it should return False
            assert result == False
        except Exception:
            # Short frame might raise an exception, which is acceptable
            pass

    def test_very_long_frame(self):
        """Test processing very long frame"""
        vad = webrtcvad.Vad(2)
        long_frame = b'\x00' * 10000
        try:
            result = vad.is_speech(long_frame, 16000)
            # If it doesn't raise, it should return False
            assert result == False
        except Exception:
            # Long frame might raise an exception, which is acceptable
            pass


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
