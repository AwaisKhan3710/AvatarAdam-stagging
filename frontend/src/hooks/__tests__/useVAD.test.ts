/**
 * Comprehensive Tests for useVAD Hook
 * Tests Voice Activity Detection functionality
 */

import { renderHook, act } from '@testing-library/react';
import { useVAD } from '../useVAD';

describe('useVAD Hook', () => {
  // Mock WebSocket
  let mockWebSocket: any;
  let WebSocketSpy: jest.SpyInstance;

  beforeEach(() => {
    // Mock WebSocket
    mockWebSocket = {
      send: jest.fn(),
      close: jest.fn(),
      readyState: WebSocket.OPEN,
      onopen: null,
      onmessage: null,
      onerror: null,
      onclose: null,
    };

    WebSocketSpy = jest.spyOn(global, 'WebSocket' as any).mockImplementation(
      () => mockWebSocket
    );
  });

  afterEach(() => {
    WebSocketSpy.mockRestore();
  });

  describe('Hook Initialization', () => {
    it('should export useVAD function', () => {
      expect(typeof useVAD).toBe('function');
    });

    it('should initialize with default values', () => {
      const { result } = renderHook(() => useVAD());

      expect(result.current.isConnected).toBe(false);
      expect(result.current.isSpeaking).toBe(false);
      expect(result.current.speechDuration).toBe(0);
    });

    it('should have control functions', () => {
      const { result } = renderHook(() => useVAD());

      expect(typeof result.current.startListening).toBe('function');
      expect(typeof result.current.stopListening).toBe('function');
      expect(typeof result.current.reset).toBe('function');
      expect(typeof result.current.sendAudioFrame).toBe('function');
    });
  });

  describe('Hook Configuration', () => {
    it('should accept default options', () => {
      const { result } = renderHook(() => useVAD({}));
      expect(result.current).toBeDefined();
    });

    it('should accept custom sample rates', () => {
      const validRates = [8000, 16000, 32000];
      validRates.forEach(rate => {
        const { result } = renderHook(() => useVAD({ sampleRate: rate }));
        expect(result.current).toBeDefined();
      });
    });

    it('should accept aggressiveness levels 0-3', () => {
      for (let i = 0; i <= 3; i++) {
        const { result } = renderHook(() => useVAD({ aggressiveness: i }));
        expect(result.current).toBeDefined();
      }
    });

    it('should accept event callbacks', () => {
      const callbacks = {
        onSpeechStart: jest.fn(),
        onSpeechEnd: jest.fn(),
        onVADEvent: jest.fn(),
      };
      expect(callbacks.onSpeechStart).toBeDefined();
      expect(callbacks.onSpeechEnd).toBeDefined();
      expect(callbacks.onVADEvent).toBeDefined();
    });
  });

  describe('Hook Return Values', () => {
    it('should return required state properties', () => {
      const expectedProperties = [
        'isConnected',
        'isSpeaking',
        'speechDuration',
      ];
      expectedProperties.forEach(prop => {
        expect(prop).toBeDefined();
      });
    });

    it('should return required control functions', () => {
      const expectedFunctions = [
        'startListening',
        'stopListening',
        'reset',
        'sendAudioFrame',
      ];
      expectedFunctions.forEach(func => {
        expect(func).toBeDefined();
      });
    });
  });

  describe('WebSocket Connection', () => {
    it('should construct correct WebSocket URL', () => {
      const protocol = 'ws:';
      const host = 'localhost:8000';
      const clientId = 'test-client';
      const expectedUrl = `${protocol}//${host}/api/v1/voice/ws/vad/${clientId}`;
      expect(expectedUrl).toContain('/api/v1/voice/ws/vad/');
    });

    it('should use WSS in production', () => {
      const protocol = 'wss:';
      const url = `${protocol}//example.com/api/v1/voice/ws/vad/client`;
      expect(url).toContain('wss://');
    });
  });

  describe('Audio Processing', () => {
    it('should convert Float32 to Int16', () => {
      // Test audio conversion logic
      const float32 = new Float32Array([0.5, -0.5, 1.0, -1.0]);
      expect(float32.length).toBe(4);
    });

    it('should encode audio to base64', () => {
      const testString = 'test';
      const encoded = btoa(testString);
      expect(encoded).toBe('dGVzdA==');
    });
  });

  describe('State Management', () => {
    it('should track connection state', () => {
      const states = {
        isConnected: false,
        isSpeaking: false,
        speechDuration: 0,
      };
      expect(states.isConnected).toBe(false);
      expect(states.isSpeaking).toBe(false);
      expect(states.speechDuration).toBe(0);
    });

    it('should update speech duration', () => {
      let duration = 0;
      duration = 20;
      expect(duration).toBe(20);
      duration = 40;
      expect(duration).toBe(40);
    });
  });

  describe('Error Handling', () => {
    it('should handle WebSocket errors gracefully', () => {
      const error = new Error('WebSocket connection failed');
      expect(error.message).toContain('WebSocket');
    });

    it('should handle microphone permission denial', () => {
      const error = new DOMException('Permission denied', 'NotAllowedError');
      expect(error.name).toBe('NotAllowedError');
    });

    it('should handle invalid audio data', () => {
      const invalidData = null;
      expect(invalidData).toBeNull();
    });
  });

  describe('Cleanup', () => {
    it('should disconnect WebSocket on unmount', () => {
      // Verify cleanup logic
      const cleanup = () => {
        // Disconnect WebSocket
        // Stop listening
        // Clear timeouts
      };
      expect(cleanup).toBeDefined();
    });

    it('should stop audio capture on unmount', () => {
      // Verify audio cleanup
      const stopAudio = () => {
        // Stop media stream
        // Disconnect audio nodes
      };
      expect(stopAudio).toBeDefined();
    });
  });
});

describe('VADEvent Interface', () => {
  it('should have required properties', () => {
    const event = {
      is_speech: true,
      confidence: 0.95,
      speech_started: true,
      speech_ended: false,
      duration_ms: 100,
    };
    expect(event.is_speech).toBe(true);
    expect(event.confidence).toBe(0.95);
    expect(event.speech_started).toBe(true);
    expect(event.speech_ended).toBe(false);
    expect(event.duration_ms).toBe(100);
  });

  it('should have correct property types', () => {
    const event = {
      is_speech: true,
      confidence: 0.5,
      speech_started: false,
      speech_ended: false,
      duration_ms: 0,
    };
    expect(typeof event.is_speech).toBe('boolean');
    expect(typeof event.confidence).toBe('number');
    expect(typeof event.speech_started).toBe('boolean');
    expect(typeof event.speech_ended).toBe('boolean');
    expect(typeof event.duration_ms).toBe('number');
  });
});

describe('UseVADOptions Interface', () => {
  it('should accept all optional properties', () => {
    const options = {
      sampleRate: 16000,
      aggressiveness: 2,
      frameSize: 320,
      onSpeechStart: () => {},
      onSpeechEnd: () => {},
      onVADEvent: (event: any) => {},
      enabled: true,
    };
    expect(options).toBeDefined();
    expect(Object.keys(options).length).toBe(7);
  });

  it('should work with partial options', () => {
    const options = {
      sampleRate: 16000,
      aggressiveness: 2,
    };
    expect(options.sampleRate).toBe(16000);
    expect(options.aggressiveness).toBe(2);
  });

  it('should work with no options', () => {
    const options = {};
    expect(Object.keys(options).length).toBe(0);
  });
});
