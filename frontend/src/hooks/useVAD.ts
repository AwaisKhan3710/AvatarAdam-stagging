import { useEffect, useRef, useState, useCallback } from 'react';

export interface VADEvent {
  is_speech: boolean;
  confidence: number;
  speech_started: boolean;
  speech_ended: boolean;
  duration_ms: number;
}

export interface UseVADOptions {
  sampleRate?: number;
  aggressiveness?: number;
  onSpeechStart?: () => void;
  onSpeechEnd?: () => void;
  onVADEvent?: (event: VADEvent) => void;
  enabled?: boolean;
}

/**
 * Hook for real-time Voice Activity Detection using WebSocket.
 *
 * Features:
 * - Real-time speech detection
 * - Callbacks for speech start/end events
 * - Configurable aggressiveness (0-3)
 * - Automatic reconnection
 * 
 * IMPORTANT: WebRTC VAD requires specific frame sizes:
 * - 10ms, 20ms, or 30ms frames
 * - At 16kHz: 160, 320, or 480 samples per frame
 * - Each sample is 2 bytes (16-bit PCM)
 * - So frame sizes in bytes: 320, 640, or 960 bytes
 */
export function useVAD(options: UseVADOptions = {}) {
  const {
    sampleRate = 16000,
    aggressiveness = 2,
    onSpeechStart,
    onSpeechEnd,
    onVADEvent,
    enabled = true,
  } = options;

  // Frame size: 20ms at 16kHz = 320 samples = 640 bytes
  const FRAME_DURATION_MS = 20;
  const SAMPLES_PER_FRAME = (sampleRate * FRAME_DURATION_MS) / 1000; // 320 samples
  const BYTES_PER_FRAME = SAMPLES_PER_FRAME * 2; // 640 bytes (16-bit audio)

  const wsRef = useRef<WebSocket | null>(null);
  const clientIdRef = useRef<string>(`vad-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`);
  const audioContextRef = useRef<AudioContext | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | ScriptProcessorNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const audioBufferRef = useRef<Int16Array>(new Int16Array(0));
  const enabledRef = useRef(enabled);
  const hasConnectedRef = useRef(false);

  const [isConnected, setIsConnected] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [speechDuration, setSpeechDuration] = useState(0);

  // Refs for callbacks to avoid stale closures
  const onSpeechStartRef = useRef(onSpeechStart);
  const onSpeechEndRef = useRef(onSpeechEnd);
  const onVADEventRef = useRef(onVADEvent);

  useEffect(() => {
    onSpeechStartRef.current = onSpeechStart;
    onSpeechEndRef.current = onSpeechEnd;
    onVADEventRef.current = onVADEvent;
  }, [onSpeechStart, onSpeechEnd, onVADEvent]);

  // Convert Float32 audio samples to Int16 PCM
  const float32ToInt16 = useCallback((float32Array: Float32Array): Int16Array => {
    const int16Array = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i++) {
      // Clamp to [-1, 1] and convert to 16-bit
      const s = Math.max(-1, Math.min(1, float32Array[i]));
      int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return int16Array;
  }, []);

  // Convert Int16Array to base64 string
  const int16ToBase64 = useCallback((int16Array: Int16Array): string => {
    const uint8Array = new Uint8Array(int16Array.buffer);
    let binary = '';
    for (let i = 0; i < uint8Array.length; i++) {
      binary += String.fromCharCode(uint8Array[i]);
    }
    return btoa(binary);
  }, []);

  // Send audio frame to VAD WebSocket
  const sendAudioFrame = useCallback((frameData: Int16Array) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return;
    }

    try {
      const base64Audio = int16ToBase64(frameData);

      wsRef.current.send(
        JSON.stringify({
          type: 'audio_frame',
          data: base64Audio,
          sample_rate: sampleRate,
          aggressiveness,
        })
      );
    } catch (error) {
      console.error('Error sending audio frame:', error);
    }
  }, [sampleRate, aggressiveness, int16ToBase64]);

  // Process audio data and send complete frames
  const processAudioData = useCallback((float32Data: Float32Array) => {
    // Convert to Int16
    const int16Data = float32ToInt16(float32Data);

    // Append to buffer
    const newBuffer = new Int16Array(audioBufferRef.current.length + int16Data.length);
    newBuffer.set(audioBufferRef.current);
    newBuffer.set(int16Data, audioBufferRef.current.length);
    audioBufferRef.current = newBuffer;

    // Send complete frames (320 samples each for 20ms at 16kHz)
    while (audioBufferRef.current.length >= SAMPLES_PER_FRAME) {
      const frame = audioBufferRef.current.slice(0, SAMPLES_PER_FRAME);
      audioBufferRef.current = audioBufferRef.current.slice(SAMPLES_PER_FRAME);
      sendAudioFrame(frame);
    }
  }, [float32ToInt16, sendAudioFrame, SAMPLES_PER_FRAME]);

  // Ref for processAudioData to avoid stale closures in event handlers
  const processAudioDataRef = useRef(processAudioData);
  useEffect(() => {
    processAudioDataRef.current = processAudioData;
  }, [processAudioData]);

  // Connect to VAD WebSocket
  const connect = useCallback(() => {
    if (!enabled) return;
    if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) {
      return;
    }

    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/api/v1/voice/ws/vad/${clientIdRef.current}`;
      
      console.log('🔌 Connecting to VAD WebSocket:', wsUrl);
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('✅ VAD WebSocket connected');
        setIsConnected(true);

        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);

          if (message.type === 'vad_event') {
            const vadEvent: VADEvent = {
              is_speech: message.is_speech,
              confidence: message.confidence,
              speech_started: message.speech_started,
              speech_ended: message.speech_ended,
              duration_ms: message.duration_ms,
            };

            // Log for debugging
            if (vadEvent.speech_started || vadEvent.speech_ended) {
              console.log('🎤 VAD Event:', vadEvent);
            }

            // Update speech state
            if (vadEvent.speech_started) {
              setIsSpeaking(true);
              setSpeechDuration(0);
              onSpeechStartRef.current?.();
            }

            if (vadEvent.speech_ended) {
              setIsSpeaking(false);
              setSpeechDuration(0);
              onSpeechEndRef.current?.();
            }

            // Update duration while speaking
            if (vadEvent.is_speech) {
              setIsSpeaking(true);
              setSpeechDuration(vadEvent.duration_ms);
            }

            onVADEventRef.current?.(vadEvent);
          } else if (message.type === 'pong') {
            console.log('🏓 VAD pong received');
          } else if (message.type === 'error') {
            console.error('❌ VAD error:', message.message);
          }
        } catch (error) {
          console.error('Error parsing VAD message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('❌ VAD WebSocket error:', error);
        setIsConnected(false);
      };

      ws.onclose = (event) => {
        console.log('🔌 VAD WebSocket closed:', event.code, event.reason);
        setIsConnected(false);
        wsRef.current = null;

        // Attempt to reconnect after 3 seconds if still enabled and was intentionally connected
        if (enabledRef.current && hasConnectedRef.current) {
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log('🔄 Attempting to reconnect VAD WebSocket...');
            connect();
          }, 3000);
        }
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('Failed to connect to VAD WebSocket:', error);
      setIsConnected(false);
    }
  }, [enabled]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setIsConnected(false);
  }, []);

  // Start listening to microphone
  const startListening = useCallback(async () => {
    try {
      // Connect WebSocket first if not connected
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        connect();
        // Wait a bit for connection
        await new Promise(resolve => setTimeout(resolve, 500));
      }

      // Create AudioContext if needed
      if (!audioContextRef.current || audioContextRef.current.state === 'closed') {
        audioContextRef.current = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)({
          sampleRate: sampleRate,
        });
      }

      // Resume if suspended
      if (audioContextRef.current.state === 'suspended') {
        await audioContextRef.current.resume();
      }

      // Get microphone stream
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: sampleRate,
        },
      });

      streamRef.current = stream;

      const source = audioContextRef.current.createMediaStreamSource(stream);

      // Use ScriptProcessorNode (deprecated but widely supported)
      // Buffer size of 4096 gives us ~256ms of audio at 16kHz
      const processor = audioContextRef.current.createScriptProcessor(4096, 1, 1);
      workletNodeRef.current = processor;

      processor.onaudioprocess = (event: AudioProcessingEvent) => {
        const inputData = event.inputBuffer.getChannelData(0);
        processAudioData(new Float32Array(inputData));
      };

      source.connect(processor);
      processor.connect(audioContextRef.current.destination);

      // Clear audio buffer
      audioBufferRef.current = new Int16Array(0);

      console.log('🎤 VAD listening started');
    } catch (error) {
      console.error('Failed to start VAD listening:', error);
    }
  }, [connect, sampleRate, processAudioData]);

  // Stop listening to microphone
  const stopListening = useCallback(() => {
    if (workletNodeRef.current) {
      workletNodeRef.current.disconnect();
      workletNodeRef.current = null;
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }

    // Clear audio buffer
    audioBufferRef.current = new Int16Array(0);

    console.log('🔇 VAD listening stopped');
  }, []);

  // Reset VAD state
  const reset = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'reset' }));
    }
    setIsSpeaking(false);
    setSpeechDuration(0);
    audioBufferRef.current = new Int16Array(0);
  }, []);

  // Keep enabledRef in sync
  useEffect(() => {
    enabledRef.current = enabled;
  }, [enabled]);

  // Initialize connection and start listening when enabled
  useEffect(() => {
    let mounted = true;
    
    const initVAD = async () => {
      if (!enabled || hasConnectedRef.current) return;
      
      hasConnectedRef.current = true;
      
      try {
        // Connect WebSocket
        connect();
        // Wait for connection to establish
        await new Promise(resolve => setTimeout(resolve, 500));
        
        if (!mounted) return;
        
        // Create AudioContext if needed
        if (!audioContextRef.current || audioContextRef.current.state === 'closed') {
          audioContextRef.current = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)({
            sampleRate: sampleRate,
          });
        }

        // Resume if suspended
        if (audioContextRef.current.state === 'suspended') {
          await audioContextRef.current.resume();
        }

        // Get microphone stream
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
            sampleRate: sampleRate,
          },
        });

        if (!mounted) {
          stream.getTracks().forEach(track => track.stop());
          return;
        }

        streamRef.current = stream;

        const source = audioContextRef.current.createMediaStreamSource(stream);

        // Use ScriptProcessorNode (deprecated but widely supported)
        const processor = audioContextRef.current.createScriptProcessor(4096, 1, 1);
        workletNodeRef.current = processor;

        processor.onaudioprocess = (event: AudioProcessingEvent) => {
          const inputData = event.inputBuffer.getChannelData(0);
          processAudioDataRef.current(new Float32Array(inputData));
        };

        source.connect(processor);
        processor.connect(audioContextRef.current.destination);

        // Clear audio buffer
        audioBufferRef.current = new Int16Array(0);

        console.log('🎤 VAD listening started');
      } catch (error) {
        console.error('Failed to start VAD:', error);
        hasConnectedRef.current = false;
      }
    };

    const cleanupVAD = () => {
      if (!hasConnectedRef.current) return;
      
      hasConnectedRef.current = false;
      
      // Stop listening
      if (workletNodeRef.current) {
        workletNodeRef.current.disconnect();
        workletNodeRef.current = null;
      }

      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
        streamRef.current = null;
      }

      // Clear audio buffer
      audioBufferRef.current = new Int16Array(0);
      
      // Disconnect WebSocket
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }

      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }

      setIsConnected(false);
      setIsSpeaking(false);
      setSpeechDuration(0);
      
      console.log('🔇 VAD stopped');
    };

    if (enabled) {
      initVAD();
    } else {
      cleanupVAD();
    }

    return () => {
      mounted = false;
      cleanupVAD();
    };
  }, [enabled, sampleRate]); // Only depend on enabled and sampleRate

  return {
    isConnected,
    isSpeaking,
    speechDuration,
    startListening,
    stopListening,
    reset,
    sendAudioFrame: processAudioData,
  };
}
