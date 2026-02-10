/**
 * VoiceChat - Main voice chat interface for Avatar Adam
 * 
 * Features:
 * - Real-time voice chat with WebSocket streaming
 * - Text chat interface
 * - Training and Role-play modes
 * - Audio playback with replay capability
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { voiceApi, chatApi, dealershipApi, avatarApi, getWsBaseUrl } from '../services/api';
import toast from 'react-hot-toast';
import { 
  Mic, MicOff, Send, Volume2, Loader2, Building2, 
  StopCircle, RotateCcw, Wifi, WifiOff, Radio, Video, VideoOff
} from 'lucide-react';
import clsx from 'clsx';
import type { Dealership, UIChatMessage } from '../types';
import ChatPanel from '../components/ChatPanel';
import { LiveAvatarSession, SessionState, SessionEvent, AgentEventsEnum } from '@heygen/liveavatar-web-sdk';

// Types
type ChatMode = 'training' | 'roleplay';
type VoiceState = 'idle' | 'connecting' | 'listening' | 'recording' | 'processing' | 'speaking';

// Generate unique message ID
const generateMessageId = () => `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

export default function VoiceChat() {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  
  // Get view from URL params (default to chat view)
  const viewParam = searchParams.get('view');
  const isChatView = viewParam !== 'avatar';
  
  // Core state
  const [mode, setMode] = useState<ChatMode>('training');
  const [voiceState, setVoiceState] = useState<VoiceState>('idle');
  const [textInput, setTextInput] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [chatMessages, setChatMessages] = useState<UIChatMessage[]>([]);
  
  // Dealership state (for super admin)
  const [dealerships, setDealerships] = useState<Dealership[]>([]);
  const [selectedDealershipId, setSelectedDealershipId] = useState<number | null>(null);
  const [isLoadingDealerships, setIsLoadingDealerships] = useState(false);
  
  // Avatar state
  const [avatarEnabled, setAvatarEnabled] = useState(false);
  const [avatarState, setAvatarState] = useState<SessionState>(SessionState.INACTIVE);
  const [isAvatarLoading, setIsAvatarLoading] = useState(false);
  
  const isSuperAdmin = user?.role === 'super_admin';
  const dealershipId = isSuperAdmin ? selectedDealershipId : user?.dealership_id;
  
  // Refs
  const wsRef = useRef<WebSocket | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);
  const audioQueueRef = useRef<string[]>([]);
  const isPlayingRef = useRef(false);
  const sessionIdRef = useRef<string | null>(null);
  const pendingMessageIdRef = useRef<string | null>(null);
  const responseAudioRef = useRef<string[]>([]);
  
  // Avatar refs
  const avatarSessionRef = useRef<LiveAvatarSession | null>(null);
  const avatarVideoRef = useRef<HTMLVideoElement | null>(null);
  const avatarEnabledRef = useRef(avatarEnabled);
  
  // Refs for stable callbacks
  const stateRefs = useRef({ mode, isListening, voiceState, transcript });
  useEffect(() => {
    stateRefs.current = { mode, isListening, voiceState, transcript };
  }, [mode, isListening, voiceState, transcript]);
  
  // Keep avatarEnabledRef in sync
  useEffect(() => {
    avatarEnabledRef.current = avatarEnabled;
  }, [avatarEnabled]);

  // Load dealerships for super admin
  useEffect(() => {
    if (isSuperAdmin) {
      setIsLoadingDealerships(true);
      dealershipApi.list()
        .then((data) => {
          setDealerships(data);
          if (data.length > 0 && !selectedDealershipId) {
            setSelectedDealershipId(data[0].id);
          }
        })
        .finally(() => setIsLoadingDealerships(false));
    }
  }, [isSuperAdmin, selectedDealershipId]);

  // Initialize avatar session on mount
  const initializeAvatar = useCallback(async () => {
    if (avatarSessionRef.current) return;
    
    setIsAvatarLoading(true);
    try {
      // Get session token from backend
      const { session_token } = await avatarApi.createSession();
      
      // Create LiveAvatar session
      const session = new LiveAvatarSession(session_token);
      avatarSessionRef.current = session;
      
      // Listen for state changes
      session.on(SessionEvent.SESSION_STATE_CHANGED, (state: SessionState) => {
        setAvatarState(state);
        if (state === SessionState.CONNECTED) {
          setIsAvatarLoading(false);
        }
      });
      
      // Listen for avatar speaking events to manage voice state
      session.on(AgentEventsEnum.AVATAR_SPEAK_STARTED, () => {
        setVoiceState('speaking');
      });
      
      session.on(AgentEventsEnum.AVATAR_SPEAK_ENDED, () => {
        setVoiceState(stateRefs.current.isListening ? 'listening' : 'idle');
      });
      
      // Listen for stream ready to attach video
      session.on(SessionEvent.SESSION_STREAM_READY, () => {
        console.log('Avatar stream ready');
        if (avatarVideoRef.current) {
          session.attach(avatarVideoRef.current);
        }
      });
      
      // Start the session
      await session.start();
      
      // Attach video element if available
      if (avatarVideoRef.current) {
        session.attach(avatarVideoRef.current);
      }
      
      toast.success('Avatar connected');
    } catch (error) {
      console.error('Failed to initialize avatar:', error);
      toast.error('Failed to connect avatar');
      setIsAvatarLoading(false);
    }
  }, []);

  const cleanupAvatar = useCallback(() => {
    if (avatarSessionRef.current) {
      try {
        avatarSessionRef.current.stop();
      } catch (e) {
        console.error('Error stopping avatar session:', e);
      }
      avatarSessionRef.current = null;
    }
    setAvatarState(SessionState.INACTIVE);
  }, []);

  // Initialize avatar on page mount, cleanup on unmount
  useEffect(() => {
    initializeAvatar();
    
    return () => {
      cleanupAvatar();
    };
  }, [initializeAvatar, cleanupAvatar]);

  // Attach video element when ref changes or avatar is enabled
  useEffect(() => {
    if (avatarVideoRef.current && avatarSessionRef.current && avatarState === SessionState.CONNECTED && avatarEnabled) {
      avatarSessionRef.current.attach(avatarVideoRef.current);
    }
  }, [avatarState, avatarEnabled]);

  // Callback ref to attach video when element is mounted
  const handleVideoRef = useCallback((element: HTMLVideoElement | null) => {
    avatarVideoRef.current = element;
    if (element && avatarSessionRef.current && avatarState === SessionState.CONNECTED) {
      avatarSessionRef.current.attach(element);
    }
  }, [avatarState]);

  // Function to make avatar speak text
  const avatarSpeak = useCallback((text: string) => {
    if (avatarSessionRef.current && avatarState === SessionState.CONNECTED) {
      try {
        avatarSessionRef.current.repeat(text);
      } catch (e) {
        console.error('Error making avatar speak:', e);
      }
    }
  }, [avatarState]);

  // Chat message helpers
  const addUserMessage = useCallback((content: string, isVoice = false) => {
    const message: UIChatMessage = {
      id: generateMessageId(),
      role: 'user',
      content,
      timestamp: new Date(),
      isVoiceMessage: isVoice,
    };
    setChatMessages(prev => [...prev, message]);
    return message.id;
  }, []);

  const addAssistantMessage = useCallback((content: string, isStreaming = false) => {
    const id = generateMessageId();
    setChatMessages(prev => [...prev, {
      id,
      role: 'assistant',
      content,
      timestamp: new Date(),
      isStreaming,
    }]);
    return id;
  }, []);

  const finalizeAssistantMessage = useCallback((messageId: string, content?: string, audio?: string) => {
    setChatMessages(prev => prev.map(msg => 
      msg.id === messageId 
        ? { ...msg, content: content ?? msg.content, isStreaming: false, audioBase64: audio }
        : msg
    ));
  }, []);

  // Audio playback
  const playAudio = useCallback((base64Audio: string, onEnded?: () => void) => {
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
    }

    const audio = new Audio(`data:audio/mp3;base64,${base64Audio}`);
    currentAudioRef.current = audio;

    audio.onplay = () => setVoiceState('speaking');
    audio.onended = () => {
      currentAudioRef.current = null;
      onEnded?.();
      setVoiceState(stateRefs.current.isListening ? 'listening' : 'idle');
    };
    audio.onerror = () => {
      currentAudioRef.current = null;
      setVoiceState(stateRefs.current.isListening ? 'listening' : 'idle');
    };

    audio.play().catch(() => {
      setVoiceState(stateRefs.current.isListening ? 'listening' : 'idle');
    });
  }, []);

  const playNextInQueue = useCallback(() => {
    if (audioQueueRef.current.length === 0) {
      isPlayingRef.current = false;
      return;
    }
    const audioData = audioQueueRef.current.shift()!;
    playAudio(audioData, playNextInQueue);
  }, [playAudio]);

  const stopAudio = useCallback(() => {
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
    }
    audioQueueRef.current = [];
    isPlayingRef.current = false;
    setVoiceState(stateRefs.current.isListening ? 'listening' : 'idle');
  }, []);

  // Interrupt Adam's response - stop audio/avatar and signal backend
  const interruptResponse = useCallback(() => {
    console.log('🛑 Interrupting Adam response');
    
    // Stop audio playback immediately
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
    }
    audioQueueRef.current = [];
    isPlayingRef.current = false;
    
    // Stop avatar speaking if enabled
    if (avatarEnabledRef.current && avatarSessionRef.current) {
      try {
        avatarSessionRef.current.interrupt();
      } catch (e) {
        console.error('Error interrupting avatar:', e);
      }
    }
    
    // Signal backend to cancel current processing
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'interrupt' }));
    }
    
    // Clear pending message
    if (pendingMessageIdRef.current) {
      setChatMessages(prev => prev.map(msg => 
        msg.id === pendingMessageIdRef.current 
          ? { ...msg, isStreaming: false, content: msg.content || '[Interrupted]' }
          : msg
      ));
      pendingMessageIdRef.current = null;
    }
    
    // Set state to listening so we can capture the new question
    setVoiceState('listening');
  }, []);

  // WebSocket message handler
  const handleWsMessage = useCallback((event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data);
      console.log('📊 Parsed message:', data.type, data);

      switch (data.type) {
        case 'ready':
          console.log('✅ Server ready');
          setIsConnected(true);
          setVoiceState(stateRefs.current.isListening ? 'listening' : 'idle');
          break;

        case 'speaking_started':
          setVoiceState('recording');
          setInterimTranscript('');
          break;

        case 'speaking_stopped':
          if (!['processing', 'speaking'].includes(stateRefs.current.voiceState)) {
            setVoiceState('listening');
          }
          break;

        case 'transcript':
          if (data.is_final) {
            const text = data.full_transcript || data.text;
            setTranscript(text);
            setInterimTranscript('');
            if (text) addUserMessage(text, true);
          } else {
            setInterimTranscript(data.text);
          }
          break;

        case 'processing':
          setVoiceState('processing');
          responseAudioRef.current = [];
          pendingMessageIdRef.current = addAssistantMessage('', true);
          break;

        case 'audio_chunk':
          if (data.data) {
            responseAudioRef.current.push(data.data);
            // Only play audio if avatar is NOT enabled
            if (!avatarEnabledRef.current) {
              audioQueueRef.current.push(data.data);
              if (!isPlayingRef.current) {
                isPlayingRef.current = true;
                setVoiceState('speaking');
                playNextInQueue();
              }
            }
          }
          break;

        case 'response_complete':
          const responseText = data.text || stateRefs.current.transcript;
          setTranscript(responseText);
          if (pendingMessageIdRef.current && responseText) {
            const audio = responseAudioRef.current[0];
            finalizeAssistantMessage(pendingMessageIdRef.current, responseText, audio);
            pendingMessageIdRef.current = null;
            responseAudioRef.current = [];
            
            // If avatar is enabled, make it speak the response (instead of audio)
            if (avatarEnabledRef.current && avatarSessionRef.current) {
              try {
                // Avatar events (AVATAR_SPEAK_STARTED/ENDED) will manage voice state
                avatarSessionRef.current.repeat(responseText);
              } catch (e) {
                console.error('Error making avatar speak:', e);
                setVoiceState(stateRefs.current.isListening ? 'listening' : 'idle');
              }
            }
          }
          break;

        case 'error':
          toast.error(data.message || 'Voice chat error');
          if (pendingMessageIdRef.current) {
            setChatMessages(prev => prev.filter(m => m.id !== pendingMessageIdRef.current));
            pendingMessageIdRef.current = null;
          }
          setVoiceState(stateRefs.current.isListening ? 'listening' : 'idle');
          break;

        case 'interrupted':
          // Server acknowledged the interrupt
          console.log('✅ Server acknowledged interrupt');
          setVoiceState('listening');
          break;

        case 'cleared':
          setTranscript('');
          setInterimTranscript('');
          setChatMessages([]);
          pendingMessageIdRef.current = null;
          break;
      }
    } catch (e) {
      console.error('WebSocket message error:', e);
    }
  }, [addUserMessage, addAssistantMessage, finalizeAssistantMessage, playNextInQueue]);

  // WebSocket connection
  const connectWebSocket = useCallback(() => {
    if (!user?.id || wsRef.current?.readyState === WebSocket.OPEN) return;
    if (wsRef.current?.readyState === WebSocket.CONNECTING) return;

    setVoiceState('connecting');
    const ws = new WebSocket(`${getWsBaseUrl()}/voice/ws/live/${user.id}`);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('✅ WebSocket connected');
      ws.send(JSON.stringify({ type: 'init', mode: stateRefs.current.mode }));
    };

    ws.onmessage = (event) => {
      console.log('📨 WebSocket message:', event.data);
      handleWsMessage(event);
    };

    ws.onclose = () => {
      console.log('🔌 WebSocket disconnected');
      setIsConnected(false);
      setIsListening(false);
      wsRef.current = null;
      stopAudioStream();
    };

    ws.onerror = (error) => {
      console.error('❌ WebSocket error:', error);
      toast.error('Connection error');
      setVoiceState('idle');
      setIsListening(false);
    };
  }, [user?.id, handleWsMessage]);

  const disconnectWebSocket = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    setIsConnected(false);
    setIsListening(false);
  }, []);

  // Audio stream management
  const stopAudioStream = useCallback(() => {
    processorRef.current?.disconnect();
    processorRef.current = null;
    audioContextRef.current?.close();
    audioContextRef.current = null;
    mediaStreamRef.current?.getTracks().forEach(track => track.stop());
    mediaStreamRef.current = null;
  }, []);

  const startListening = useCallback(async () => {
    if (!isConnected) {
      connectWebSocket();
      setTimeout(startListening, 1000);
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, sampleRate: 16000 },
      });
      mediaStreamRef.current = stream;

      const audioContext = new AudioContext({ sampleRate: 16000 });
      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      // VAD state tracking
      let isRecording = false;
      let silenceFrames = 0;
      const SILENCE_THRESHOLD = 0.02; // RMS threshold for silence
      const SILENCE_FRAMES_NEEDED = 10; // ~200ms of silence at 16kHz with 4096 samples

      processor.onaudioprocess = (e) => {
        if (wsRef.current?.readyState !== WebSocket.OPEN) {
          return;
        }

        const inputData = e.inputBuffer.getChannelData(0);
        
        // Calculate RMS (Root Mean Square) to detect if audio is silent
        let sum = 0;
        for (let i = 0; i < inputData.length; i++) {
          sum += inputData[i] * inputData[i];
        }
        const rms = Math.sqrt(sum / inputData.length);
        const isSilent = rms < SILENCE_THRESHOLD;

        // Check if Adam is currently responding (audio playing, avatar speaking, or processing)
        const currentState = stateRefs.current.voiceState;
        const isAdamResponding = currentState === 'speaking' || currentState === 'processing';
        const isAudioPlaying = currentAudioRef.current !== null && !currentAudioRef.current.paused;
        const hasQueuedAudio = audioQueueRef.current.length > 0 || isPlayingRef.current;
        
        // If Adam is responding and user starts talking, interrupt immediately!
        if ((isAdamResponding || isAudioPlaying || hasQueuedAudio) && !isSilent) {
          console.log('🛑 User speaking while Adam responding - INTERRUPTING!', {
            state: currentState,
            isAudioPlaying,
            hasQueuedAudio,
            rms: rms.toFixed(4)
          });
          
          // Stop everything immediately
          interruptResponse();
          
          // Don't return - continue to process this audio as new speech!
        }

        // Convert to Int16
        const int16Data = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
          int16Data[i] = Math.max(-32768, Math.min(32767, inputData[i] * 32768));
        }

        // Send as base64 encoded JSON message
        const base64Audio = btoa(String.fromCharCode.apply(null, Array.from(new Uint8Array(int16Data.buffer))));

        if (!isSilent) {
          // Audio detected
          if (!isRecording) {
            // Start recording
            isRecording = true;
            silenceFrames = 0;
            console.log('🎤 Speech detected - starting recording');
            wsRef.current.send(JSON.stringify({ type: 'start_recording' }));
          } else {
            // Continue recording - reset silence counter
            silenceFrames = 0;
          }

          // Send audio chunk
          wsRef.current.send(JSON.stringify({
            type: 'audio',
            data: base64Audio,
            sample_rate: 16000
          }));
        } else {
          // Silence detected
          if (isRecording) {
            silenceFrames++;

            if (silenceFrames >= SILENCE_FRAMES_NEEDED) {
              // Stop recording after sustained silence
              isRecording = false;
              silenceFrames = 0;
              console.log('⏹️ Silence detected - stopping recording');
              wsRef.current.send(JSON.stringify({ type: 'stop_recording' }));
            }
          }
        }
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      setIsListening(true);
      setVoiceState('listening');
      toast.success('Listening... speak naturally');
    } catch (error) {
      console.error('Failed to start listening:', error);
      toast.error('Failed to access microphone');
    }
  }, [isConnected, connectWebSocket, voiceState, interruptResponse]);

  const stopListening = useCallback(() => {
    stopAudioStream();
    setIsListening(false);
    setVoiceState('idle');
  }, [stopAudioStream]);

  // Text message handling
  const sendTextMessage = useCallback(async () => {
    if (!textInput.trim() || voiceState !== 'idle') return;

    const message = textInput;
    setTextInput('');
    setVoiceState('processing');
    addUserMessage(message);
    const assistantMsgId = addAssistantMessage('', true);

    try {
      const chatResponse = await chatApi.send({
        message,
        mode,
        session_id: sessionIdRef.current || undefined,
        dealership_id: dealershipId || undefined,
      });

      sessionIdRef.current = chatResponse.session_id;
      
      // If avatar is enabled, make it speak the response
      if (avatarEnabled && avatarSessionRef.current && avatarState === SessionState.CONNECTED) {
        finalizeAssistantMessage(assistantMsgId, chatResponse.response);
        // Avatar events (AVATAR_SPEAK_STARTED/ENDED) will manage voice state
        avatarSpeak(chatResponse.response);
      } else {
        // Use regular TTS audio playback
        const ttsResponse = await voiceApi.textToSpeech(chatResponse.response);
        finalizeAssistantMessage(assistantMsgId, chatResponse.response, ttsResponse.audio_base64);
        playAudio(ttsResponse.audio_base64);
      }
    } catch (error: unknown) {
      const err = error as { response?: { data?: { error?: { message?: string } } } };
      toast.error(err.response?.data?.error?.message || 'Failed to send message');
      setChatMessages(prev => prev.filter(m => m.id !== assistantMsgId));
      setVoiceState('idle');
    }
  }, [textInput, voiceState, mode, dealershipId, addUserMessage, addAssistantMessage, finalizeAssistantMessage, playAudio, avatarEnabled, avatarState, avatarSpeak]);

  // Voice message from chat panel
  const handleVoiceMessage = useCallback(async (audioBlob: Blob) => {
    setVoiceState('processing');
    
    // Add placeholder user message first (will be updated with transcript)
    const userMsgId = addUserMessage('🎤 Processing voice...', true);
    const assistantMsgId = addAssistantMessage('', true);

    try {
      const arrayBuffer = await audioBlob.arrayBuffer();
      const base64Audio = btoa(
        new Uint8Array(arrayBuffer).reduce((data, byte) => data + String.fromCharCode(byte), '')
      );

      const response = await voiceApi.chatFast({
        audio_base64: base64Audio,
        mode,
        session_id: sessionIdRef.current || undefined,
        mime_type: 'audio/webm',
        dealership_id: dealershipId || undefined,
      });

      sessionIdRef.current = response.session_id;
      setTranscript(response.user_transcript);
      
      // Update user message with actual transcript
      if (response.user_transcript) {
        setChatMessages(prev => prev.map(msg => 
          msg.id === userMsgId 
            ? { ...msg, content: response.user_transcript }
            : msg
        ));
      }
      
      // If avatar is enabled, make it speak the response
      if (avatarEnabled && avatarSessionRef.current && avatarState === SessionState.CONNECTED && response.response_text) {
        finalizeAssistantMessage(assistantMsgId, response.response_text);
        // Avatar events (AVATAR_SPEAK_STARTED/ENDED) will manage voice state
        avatarSpeak(response.response_text);
      } else {
        // Use regular TTS audio playback
        if (response.response_text) {
          finalizeAssistantMessage(assistantMsgId, response.response_text, response.response_audio_base64);
        }
        playAudio(response.response_audio_base64);
      }
    } catch (error: unknown) {
      const err = error as { response?: { data?: { error?: { message?: string } } } };
      toast.error(err.response?.data?.error?.message || 'Failed to process audio');
      // Remove both placeholder messages on error
      setChatMessages(prev => prev.filter(m => m.id !== assistantMsgId && m.id !== userMsgId));
      setVoiceState('idle');
    }
  }, [mode, dealershipId, addUserMessage, addAssistantMessage, finalizeAssistantMessage, playAudio, avatarEnabled, avatarState, avatarSpeak]);

  // Reset conversation
  const resetConversation = useCallback(() => {
    stopAudio();
    setTranscript('');
    setInterimTranscript('');
    setChatMessages([]);
    pendingMessageIdRef.current = null;
    sessionIdRef.current = null;
    wsRef.current?.send(JSON.stringify({ type: 'clear' }));
  }, [stopAudio]);

  // Connect on mount
  useEffect(() => {
    if (user?.id) {
      const timer = setTimeout(connectWebSocket, 100);
      return () => {
        clearTimeout(timer);
        disconnectWebSocket();
        stopAudioStream();
      };
    }
  }, [user?.id, connectWebSocket, disconnectWebSocket, stopAudioStream]);

  // Update mode on server
  useEffect(() => {
    if (isConnected && wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'init', mode }));
    }
  }, [mode, isConnected]);

  // Access check
  if (!isSuperAdmin && !user?.dealership_id) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 max-w-md">
          <p className="text-yellow-800 text-center">You are not associated with a dealership.</p>
        </div>
      </div>
    );
  }

  if (isSuperAdmin && isLoadingDealerships) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
          <p className="text-gray-600">Loading dealerships...</p>
        </div>
      </div>
    );
  }

  if (isSuperAdmin && dealerships.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 max-w-md">
          <p className="text-yellow-800 text-center">No dealerships found.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 top-16 lg:top-0 lg:left-64 flex flex-col bg-gray-50">
      {/* Header */}
      <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-4 shrink-0">
        <div className="flex items-center gap-3">
          {/* Connection Status */}
          <div className={clsx(
            'flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium',
            isConnected ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
          )}>
            {isConnected ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
            <span>{isConnected ? (isListening ? 'Listening' : 'Connected') : 'Connecting...'}</span>
          </div>

          {/* Dealership Selector (Super Admin) */}
          {isSuperAdmin && dealerships.length > 0 && (
            <div className="flex items-center gap-2">
              <Building2 className="w-4 h-4 text-gray-400" />
              <select
                value={selectedDealershipId || ''}
                onChange={(e) => setSelectedDealershipId(Number(e.target.value))}
                className="text-sm px-2 py-1 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 bg-white"
              >
                {dealerships.map((d) => (
                  <option key={d.id} value={d.id}>{d.name}</option>
                ))}
              </select>
            </div>
          )}

          {/* Reset Button */}
          <button
            onClick={resetConversation}
            className="p-2 text-gray-400 hover:text-gray-600 rounded-md hover:bg-gray-100"
            title="Reset conversation"
          >
            <RotateCcw className="w-4 h-4" />
          </button>

          {/* Avatar Toggle */}
          <button
            onClick={() => setAvatarEnabled(!avatarEnabled)}
            disabled={isAvatarLoading || avatarState !== SessionState.CONNECTED}
            className={clsx(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-colors',
              avatarEnabled 
                ? 'bg-purple-100 text-purple-700' 
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200',
              (isAvatarLoading || avatarState !== SessionState.CONNECTED) && 'opacity-50 cursor-not-allowed'
            )}
            title={avatarState === SessionState.CONNECTED ? 'Toggle avatar' : 'Avatar connecting...'}
          >
            {isAvatarLoading ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : avatarEnabled ? (
              <Video className="w-3 h-3" />
            ) : (
              <VideoOff className="w-3 h-3" />
            )}
            <span>{isAvatarLoading ? 'Connecting...' : avatarEnabled ? 'Avatar On' : 'Avatar Off'}</span>
          </button>
        </div>

        {/* Mode Toggle */}
        <div className="flex bg-gray-100 rounded-full p-1">
          <button
            onClick={() => {
              if (mode !== 'training') {
                setMode('training');
                resetConversation();
              }
            }}
            className={clsx(
              'px-4 py-1.5 text-sm font-medium rounded-full transition-colors',
              mode === 'training' ? 'bg-white text-primary-600 shadow-sm' : 'text-gray-500'
            )}
          >
            Training
          </button>
          <button
            onClick={() => {
              if (mode !== 'roleplay') {
                setMode('roleplay');
                resetConversation();
              }
            }}
            className={clsx(
              'px-4 py-1.5 text-sm font-medium rounded-full transition-colors',
              mode === 'roleplay' ? 'bg-white text-primary-600 shadow-sm' : 'text-gray-500'
            )}
          >
            Role-Play
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex overflow-hidden">
        {isChatView ? (
          <div className="flex-1 w-full">
            <ChatPanel
              messages={chatMessages}
              textInput={textInput}
              onTextInputChange={setTextInput}
              onSendMessage={sendTextMessage}
              onSendVoiceMessage={handleVoiceMessage}
              isDisabled={voiceState !== 'idle'}
              mode={mode}
              interimTranscript={interimTranscript}
              voiceState={voiceState}
              sessionId={sessionIdRef.current || undefined}
              dealershipName={dealerships.find(d => d.id === dealershipId)?.name}
            />
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center w-full">
            {/* Avatar Video or Placeholder */}
            {avatarEnabled && avatarState === SessionState.CONNECTED ? (
              <div className="relative w-64 h-64 lg:w-80 lg:h-80 rounded-2xl overflow-hidden shadow-2xl bg-black">
                <video
                  ref={handleVideoRef}
                  autoPlay
                  playsInline
                  muted={false}
                  className="w-full h-full object-cover"
                />
                {/* Status overlay */}
                <div className={clsx(
                  'absolute bottom-2 left-2 px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1',
                  voiceState === 'speaking' && 'bg-primary-500 text-white',
                  voiceState === 'processing' && 'bg-amber-400 text-white',
                  voiceState === 'idle' && 'bg-green-500 text-white'
                )}>
                  {voiceState === 'speaking' && <Volume2 className="w-3 h-3 animate-pulse" />}
                  {voiceState === 'processing' && <Loader2 className="w-3 h-3 animate-spin" />}
                  {voiceState === 'idle' && <Video className="w-3 h-3" />}
                  <span>
                    {voiceState === 'speaking' && 'Speaking'}
                    {voiceState === 'processing' && 'Thinking'}
                    {voiceState === 'idle' && 'Ready'}
                  </span>
                </div>
              </div>
            ) : (
              <div
                className={clsx(
                  'w-40 h-40 lg:w-48 lg:h-48 rounded-full flex items-center justify-center transition-all duration-300',
                  voiceState === 'speaking' && 'bg-primary-500 shadow-2xl shadow-primary-500/40',
                  voiceState === 'processing' && 'bg-amber-400 shadow-xl shadow-amber-400/30',
                  voiceState === 'recording' && 'bg-red-500 shadow-2xl shadow-red-500/40',
                  voiceState === 'connecting' && 'bg-blue-400 shadow-xl shadow-blue-400/30',
                  voiceState === 'listening' && 'bg-green-500 shadow-xl shadow-green-500/30',
                  voiceState === 'idle' && 'bg-gray-200'
                )}
              >
                {voiceState === 'speaking' && <Volume2 className="w-20 h-20 text-white animate-pulse" />}
                {voiceState === 'processing' && <Loader2 className="w-20 h-20 text-white animate-spin" />}
                {voiceState === 'recording' && <Mic className="w-20 h-20 text-white animate-pulse" />}
                {voiceState === 'connecting' && <Loader2 className="w-20 h-20 text-white animate-spin" />}
                {voiceState === 'listening' && <Radio className="w-20 h-20 text-white animate-pulse" />}
                {voiceState === 'idle' && <span className="text-7xl">{mode === 'training' ? '🎓' : '🛒'}</span>}
              </div>
            )}

            {/* Name & Status */}
            <h2 className="text-2xl font-semibold text-gray-900 mt-6 mb-1">
              {mode === 'training' ? 'Adam' : 'Customer'}
            </h2>
            <p className={clsx(
              'text-sm',
              voiceState === 'speaking' && 'text-primary-600',
              voiceState === 'processing' && 'text-amber-600',
              voiceState === 'recording' && 'text-red-500',
              voiceState === 'connecting' && 'text-blue-500',
              voiceState === 'listening' && 'text-green-600',
              voiceState === 'idle' && 'text-gray-400'
            )}>
              {voiceState === 'speaking' && 'Speaking...'}
              {voiceState === 'processing' && 'Thinking...'}
              {voiceState === 'recording' && 'Listening...'}
              {voiceState === 'connecting' && 'Connecting...'}
              {voiceState === 'listening' && 'Listening (speak anytime)...'}
              {voiceState === 'idle' && (mode === 'training' ? 'AI F&I Trainer' : 'Practice Customer')}
            </p>

          </div>
        )}
      </main>

      {/* User Caption Display (Avatar View Only) - Below avatar, above buttons */}
      {!isChatView && (interimTranscript || transcript) && (
        <div className="bg-gray-50 border-t border-gray-100 px-6 py-3 text-center shrink-0">
          {interimTranscript ? (
            <p className="text-sm text-green-600 italic animate-pulse">"{interimTranscript}"</p>
          ) : (
            <p className="text-sm text-gray-600 italic">"{transcript}"</p>
          )}
        </div>
      )}

      {/* Bottom Controls (Avatar View Only) */}
      {!isChatView && (
        <footer className="bg-white border-t border-gray-200 flex items-center justify-center gap-4 px-6 py-4 shrink-0">
          {/* Text Input */}
          <div className="flex items-center gap-2 flex-1 max-w-lg">
            <input
              type="text"
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && sendTextMessage()}
              placeholder="Type a message..."
              disabled={voiceState !== 'idle'}
              className="flex-1 px-4 py-3 border border-gray-300 rounded-full text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:bg-gray-100"
            />
            <button
              onClick={sendTextMessage}
              disabled={!textInput.trim() || voiceState !== 'idle'}
              className="w-12 h-12 bg-primary-600 text-white rounded-full flex items-center justify-center hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>

          <div className="h-10 w-px bg-gray-300" />

          {/* Mic Button */}
          {voiceState === 'speaking' ? (
            <button
              onClick={stopAudio}
              className="w-14 h-14 rounded-full bg-red-500 text-white flex items-center justify-center shadow-lg hover:bg-red-600 transition-all"
            >
              <StopCircle className="w-7 h-7" />
            </button>
          ) : (
            <button
              onClick={isListening ? stopListening : startListening}
              disabled={voiceState === 'processing' || voiceState === 'connecting'}
              className={clsx(
                'w-14 h-14 rounded-full flex items-center justify-center transition-all shadow-lg',
                isListening && 'bg-green-500 text-white scale-110 animate-pulse',
                voiceState === 'processing' && 'bg-amber-400 text-white cursor-wait',
                voiceState === 'connecting' && 'bg-blue-400 text-white cursor-wait',
                !isListening && voiceState === 'idle' && 'bg-green-600 text-white hover:bg-green-700 hover:scale-105'
              )}
            >
              {isListening ? (
                <MicOff className="w-7 h-7" />
              ) : voiceState === 'processing' || voiceState === 'connecting' ? (
                <Loader2 className="w-7 h-7 animate-spin" />
              ) : (
                <Mic className="w-7 h-7" />
              )}
            </button>
          )}
        </footer>
      )}
    </div>
  );
}
