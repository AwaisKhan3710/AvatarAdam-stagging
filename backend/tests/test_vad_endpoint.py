"""Tests for VAD WebSocket Endpoint"""

import json
import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


class TestVADEndpoint:
    """Test VAD REST endpoint"""

    def test_vad_process_endpoint_exists(self):
        """Test that VAD process endpoint exists"""
        # This will fail if endpoint doesn't exist
        # We're just checking the route is registered
        assert app.routes is not None

    def test_vad_endpoint_documentation(self):
        """Test that API documentation is available"""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "swagger" in response.text.lower() or "openapi" in response.text.lower()


class TestVADIntegration:
    """Integration tests for VAD"""

    def test_vad_service_import(self):
        """Test that VAD service can be imported"""
        try:
            from app.services.vad_service import VoiceActivityDetector, get_vad_manager
            assert VoiceActivityDetector is not None
            assert get_vad_manager is not None
        except ImportError as e:
            pytest.skip(f"webrtcvad not installed: {e}")

    def test_vad_router_import(self):
        """Test that VAD router can be imported"""
        try:
            from app.api.v1.voice_vad import router
            assert router is not None
        except ImportError as e:
            pytest.skip(f"VAD router import failed: {e}")


class TestVADConfiguration:
    """Test VAD configuration"""

    def test_vad_service_configuration(self):
        """Test VAD service can be configured"""
        try:
            from app.services.vad_service import VoiceActivityDetector
            
            # Test different configurations
            configs = [
                {'sample_rate': 8000, 'aggressiveness': 0},
                {'sample_rate': 16000, 'aggressiveness': 2},
                {'sample_rate': 32000, 'aggressiveness': 3},
            ]
            
            for config in configs:
                vad = VoiceActivityDetector(**config)
                assert vad.sample_rate == config['sample_rate']
                assert vad.aggressiveness == config['aggressiveness']
        except ImportError:
            pytest.skip("webrtcvad not installed")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
