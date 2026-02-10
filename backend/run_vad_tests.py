#!/usr/bin/env python3
"""
Manual testing script for VAD Service

Run this script to test VAD functionality:
    python backend/run_vad_tests.py
"""

import sys
import time
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))


def test_vad_import():
    """Test if webrtcvad can be imported"""
    print("\n" + "="*60)
    print("TEST 1: Checking webrtcvad installation")
    print("="*60)
    
    try:
        import webrtcvad
        print("✅ webrtcvad is installed")
        print(f"   Version: {webrtcvad.__version__ if hasattr(webrtcvad, '__version__') else 'unknown'}")
        return True
    except ImportError as e:
        print(f"❌ webrtcvad is NOT installed")
        print(f"   Error: {e}")
        print(f"   Install with: pip install webrtcvad>=4.3.1")
        return False


def test_vad_service_import():
    """Test if VAD service can be imported"""
    print("\n" + "="*60)
    print("TEST 2: Importing VAD Service")
    print("="*60)
    
    try:
        from app.services.vad_service import VoiceActivityDetector, VADManager, get_vad_manager
        print("✅ VAD Service imported successfully")
        print(f"   - VoiceActivityDetector: {VoiceActivityDetector}")
        print(f"   - VADManager: {VADManager}")
        print(f"   - get_vad_manager: {get_vad_manager}")
        return True
    except Exception as e:
        print(f"❌ Failed to import VAD Service")
        print(f"   Error: {e}")
        return False


def test_vad_initialization():
    """Test VAD initialization"""
    print("\n" + "="*60)
    print("TEST 3: VAD Initialization")
    print("="*60)
    
    try:
        from app.services.vad_service import VoiceActivityDetector
        
        # Test default initialization
        vad = VoiceActivityDetector()
        print("✅ Default initialization successful")
        print(f"   - Sample rate: {vad.sample_rate} Hz")
        print(f"   - Aggressiveness: {vad.aggressiveness}")
        print(f"   - Frame size: {vad.frame_size} samples")
        print(f"   - Frame duration: {vad.frame_duration_ms} ms")
        
        # Test custom initialization
        vad_custom = VoiceActivityDetector(sample_rate=8000, aggressiveness=3)
        print("✅ Custom initialization successful")
        print(f"   - Sample rate: {vad_custom.sample_rate} Hz")
        print(f"   - Aggressiveness: {vad_custom.aggressiveness}")
        
        return True
    except Exception as e:
        print(f"❌ VAD initialization failed")
        print(f"   Error: {e}")
        return False


def test_vad_frame_processing():
    """Test VAD frame processing"""
    print("\n" + "="*60)
    print("TEST 4: VAD Frame Processing")
    print("="*60)
    
    try:
        from app.services.vad_service import VoiceActivityDetector
        
        vad = VoiceActivityDetector()
        
        # Create silent frame
        silent_frame = b'\x00' * vad.bytes_per_frame
        result = vad.process_frame(silent_frame)
        
        print("✅ Frame processing successful")
        print(f"   - is_speech: {result['is_speech']}")
        print(f"   - confidence: {result['confidence']}")
        print(f"   - speech_started: {result['speech_started']}")
        print(f"   - speech_ended: {result['speech_ended']}")
        print(f"   - duration_ms: {result['duration_ms']}")
        
        # Test multiple frames
        print("\n   Processing 10 frames...")
        for i in range(10):
            result = vad.process_frame(silent_frame)
            print(f"   Frame {i+1}: is_speech={result['is_speech']}, duration={result['duration_ms']}ms")
        
        return True
    except Exception as e:
        print(f"❌ Frame processing failed")
        print(f"   Error: {e}")
        return False


def test_vad_manager():
    """Test VAD Manager"""
    print("\n" + "="*60)
    print("TEST 5: VAD Manager")
    print("="*60)
    
    try:
        from app.services.vad_service import VADManager
        
        manager = VADManager()
        print("✅ VADManager created successfully")
        
        # Test getting detector
        detector1 = manager.get_detector('stream1')
        print(f"✅ Got detector for stream1: {detector1}")
        
        # Test getting same detector
        detector2 = manager.get_detector('stream1')
        print(f"✅ Got same detector again: {detector1 is detector2}")
        
        # Test multiple streams
        detector3 = manager.get_detector('stream2')
        print(f"✅ Got detector for stream2: {detector3}")
        print(f"   - Different from stream1: {detector1 is not detector3}")
        
        # Test removing detector
        manager.remove_detector('stream1')
        print(f"✅ Removed detector for stream1")
        print(f"   - Active detectors: {list(manager.detectors.keys())}")
        
        return True
    except Exception as e:
        print(f"❌ VAD Manager test failed")
        print(f"   Error: {e}")
        return False


def test_vad_endpoint_import():
    """Test VAD endpoint import"""
    print("\n" + "="*60)
    print("TEST 6: VAD Endpoint Import")
    print("="*60)
    
    try:
        from app.api.v1.voice_vad import router
        print("✅ VAD endpoint router imported successfully")
        print(f"   - Router: {router}")
        print(f"   - Routes: {len(router.routes) if hasattr(router, 'routes') else 'unknown'}")
        return True
    except Exception as e:
        print(f"❌ VAD endpoint import failed")
        print(f"   Error: {e}")
        return False


def test_vad_router_registration():
    """Test VAD router registration"""
    print("\n" + "="*60)
    print("TEST 7: VAD Router Registration")
    print("="*60)
    
    try:
        from app.api.v1 import api_router
        print("✅ API router imported successfully")
        
        # Check if VAD routes are registered
        routes = [route.path for route in api_router.routes]
        vad_routes = [r for r in routes if 'vad' in r.lower() or 'voice' in r.lower()]
        
        if vad_routes:
            print(f"✅ VAD routes registered: {len(vad_routes)} routes found")
            for route in vad_routes[:5]:  # Show first 5
                print(f"   - {route}")
        else:
            print("⚠️  No VAD routes found in API router")
        
        return True
    except Exception as e:
        print(f"❌ Router registration test failed")
        print(f"   Error: {e}")
        return False


def test_vad_configuration_options():
    """Test VAD configuration options"""
    print("\n" + "="*60)
    print("TEST 8: VAD Configuration Options")
    print("="*60)
    
    try:
        from app.services.vad_service import VoiceActivityDetector
        
        configs = [
            {'sample_rate': 8000, 'aggressiveness': 0, 'name': 'Telephone (8kHz, Permissive)'},
            {'sample_rate': 16000, 'aggressiveness': 1, 'name': 'CD Quality (16kHz, Sensitive)'},
            {'sample_rate': 16000, 'aggressiveness': 2, 'name': 'CD Quality (16kHz, Balanced)'},
            {'sample_rate': 16000, 'aggressiveness': 3, 'name': 'CD Quality (16kHz, Aggressive)'},
            {'sample_rate': 32000, 'aggressiveness': 2, 'name': 'High Quality (32kHz, Balanced)'},
        ]
        
        print("✅ Testing different configurations:")
        for config in configs:
            name = config.pop('name')
            vad = VoiceActivityDetector(**config)
            print(f"   ✅ {name}")
            print(f"      Frame size: {vad.frame_size} samples, Bytes: {vad.bytes_per_frame}")
        
        return True
    except Exception as e:
        print(f"❌ Configuration test failed")
        print(f"   Error: {e}")
        return False


def test_vad_state_management():
    """Test VAD state management"""
    print("\n" + "="*60)
    print("TEST 9: VAD State Management")
    print("="*60)
    
    try:
        from app.services.vad_service import VoiceActivityDetector
        
        vad = VoiceActivityDetector()
        
        # Test initial state
        print("✅ Initial state:")
        print(f"   - is_speech: {vad.is_speech}")
        print(f"   - speech_start_frame: {vad.speech_start_frame}")
        print(f"   - silence_frames: {vad.silence_frames}")
        
        # Test reset
        vad.is_speech = True
        vad.speech_start_frame = 10
        vad.silence_frames = 5
        
        vad.reset()
        print("✅ After reset:")
        print(f"   - is_speech: {vad.is_speech}")
        print(f"   - speech_start_frame: {vad.speech_start_frame}")
        print(f"   - silence_frames: {vad.silence_frames}")
        
        return True
    except Exception as e:
        print(f"❌ State management test failed")
        print(f"   Error: {e}")
        return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("VAD SERVICE TESTING SUITE")
    print("="*60)
    print(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("webrtcvad Installation", test_vad_import),
        ("VAD Service Import", test_vad_service_import),
        ("VAD Initialization", test_vad_initialization),
        ("VAD Frame Processing", test_vad_frame_processing),
        ("VAD Manager", test_vad_manager),
        ("VAD Endpoint Import", test_vad_endpoint_import),
        ("VAD Router Registration", test_vad_router_registration),
        ("VAD Configuration Options", test_vad_configuration_options),
        ("VAD State Management", test_vad_state_management),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Test '{name}' crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print(f"Ended at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    exit_code = run_all_tests()
    sys.exit(exit_code)
