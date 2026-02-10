"""Manual VAD Testing Script - Run this to test VAD functionality"""

import sys
import time
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))


def test_imports():
    """Test 1: Check if webrtcvad is installed"""
    print("\n" + "="*60)
    print("TEST 1: Checking webrtcvad installation")
    print("="*60)
    
    try:
        import webrtcvad
        print("✓ webrtcvad imported successfully")
        print(f"  Version: {webrtcvad.__version__ if hasattr(webrtcvad, '__version__') else 'Unknown'}")
        return True
    except ImportError as e:
        print(f"✗ Failed to import webrtcvad: {e}")
        print("  Install with: pip install webrtcvad>=4.3.1")
        return False


def test_vad_service():
    """Test 2: Test VAD Service"""
    print("\n" + "="*60)
    print("TEST 2: Testing VAD Service")
    print("="*60)
    
    try:
        from app.services.vad_service import VoiceActivityDetector, VADManager
        print("✓ VAD service imported successfully")
        
        # Test VoiceActivityDetector initialization
        print("\n  Testing VoiceActivityDetector initialization...")
        vad = VoiceActivityDetector(sample_rate=16000, aggressiveness=2)
        print(f"  ✓ VoiceActivityDetector created")
        print(f"    - Sample rate: {vad.sample_rate} Hz")
        print(f"    - Aggressiveness: {vad.aggressiveness}")
        print(f"    - Frame size: {vad.frame_size} samples")
        print(f"    - Bytes per frame: {vad.bytes_per_frame}")
        
        # Test VADManager
        print("\n  Testing VADManager...")
        manager = VADManager()
        detector = manager.get_detector("test-stream")
        print(f"  ✓ VADManager created and detector retrieved")
        
        # Test frame processing with silence
        print("\n  Testing frame processing with silence...")
        silence_frame = b'\x00' * vad.bytes_per_frame
        result = vad.process_frame(silence_frame)
        print(f"  ✓ Silence frame processed")
        print(f"    - is_speech: {result['is_speech']}")
        print(f"    - confidence: {result['confidence']}")
        
        # Test reset
        print("\n  Testing reset...")
        vad.reset()
        print(f"  ✓ VAD reset successful")
        
        return True
    except Exception as e:
        print(f"✗ VAD service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_vad_configurations():
    """Test 3: Test different VAD configurations"""
    print("\n" + "="*60)
    print("TEST 3: Testing VAD Configurations")
    print("="*60)
    
    try:
        from app.services.vad_service import VoiceActivityDetector
        
        # Test different sample rates
        print("\n  Testing different sample rates...")
        for sample_rate in [8000, 16000, 32000]:
            vad = VoiceActivityDetector(sample_rate=sample_rate, aggressiveness=2)
            print(f"  ✓ Sample rate {sample_rate} Hz: OK")
        
        # Test different aggressiveness levels
        print("\n  Testing different aggressiveness levels...")
        for aggressiveness in [0, 1, 2, 3]:
            vad = VoiceActivityDetector(sample_rate=16000, aggressiveness=aggressiveness)
            print(f"  ✓ Aggressiveness {aggressiveness}: OK")
        
        # Test invalid configurations
        print("\n  Testing invalid configurations...")
        try:
            vad = VoiceActivityDetector(sample_rate=44100)  # Invalid
            print(f"  ✗ Should have rejected invalid sample rate")
            return False
        except ValueError:
            print(f"  ✓ Correctly rejected invalid sample rate")
        
        try:
            vad = VoiceActivityDetector(aggressiveness=5)  # Invalid
            print(f"  ✗ Should have rejected invalid aggressiveness")
            return False
        except ValueError:
            print(f"  ✓ Correctly rejected invalid aggressiveness")
        
        return True
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_vad_manager():
    """Test 4: Test VAD Manager"""
    print("\n" + "="*60)
    print("TEST 4: Testing VAD Manager")
    print("="*60)
    
    try:
        from app.services.vad_service import VADManager
        
        manager = VADManager()
        print("✓ VADManager created")
        
        # Test multiple detectors
        print("\n  Testing multiple detector instances...")
        detector1 = manager.get_detector("stream-1")
        detector2 = manager.get_detector("stream-2")
        print(f"  ✓ Created 2 detector instances")
        print(f"    - Active detectors: {len(manager.detectors)}")
        
        # Test detector removal
        print("\n  Testing detector removal...")
        manager.remove_detector("stream-1")
        print(f"  ✓ Removed detector")
        print(f"    - Active detectors: {len(manager.detectors)}")
        
        # Test reset
        print("\n  Testing detector reset...")
        manager.reset_detector("stream-2")
        print(f"  ✓ Reset detector")
        
        return True
    except Exception as e:
        print(f"✗ VAD Manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_router():
    """Test 5: Test API Router Registration"""
    print("\n" + "="*60)
    print("TEST 5: Testing API Router Registration")
    print("="*60)
    
    try:
        from app.api.v1 import api_router
        print("✓ API router imported successfully")
        
        # Check if VAD router is registered
        routes = [route.path for route in api_router.routes]
        vad_routes = [r for r in routes if 'vad' in r.lower()]
        
        if vad_routes:
            print(f"✓ VAD routes registered: {len(vad_routes)} routes")
            for route in vad_routes:
                print(f"  - {route}")
        else:
            print("✗ No VAD routes found")
            return False
        
        return True
    except Exception as e:
        print(f"✗ API router test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_websocket_endpoint():
    """Test 6: Test WebSocket Endpoint"""
    print("\n" + "="*60)
    print("TEST 6: Testing WebSocket Endpoint")
    print("="*60)
    
    try:
        from app.api.v1.voice_vad import router
        print("✓ WebSocket endpoint imported successfully")
        
        # Check routes
        routes = [route.path for route in router.routes]
        print(f"✓ Found {len(routes)} routes in VAD router")
        for route in routes:
            print(f"  - {route}")
        
        return True
    except Exception as e:
        print(f"✗ WebSocket endpoint test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("VOICE ACTIVITY DETECTION - MANUAL TEST SUITE")
    print("="*60)
    print(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("Imports", test_imports),
        ("VAD Service", test_vad_service),
        ("VAD Configurations", test_vad_configurations),
        ("VAD Manager", test_vad_manager),
        ("API Router", test_api_router),
        ("WebSocket Endpoint", test_websocket_endpoint),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed! VAD is working correctly.")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
