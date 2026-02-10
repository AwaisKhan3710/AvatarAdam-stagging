/**
 * useVoiceChat - Shared hook for voice chat functionality
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { voiceApi, chatApi, dealershipApi, avatarApi, getWsBaseUrl } from '../services/api';
import { LiveAvatarSession, SessionState, SessionEvent, AgentEventsEnum } from '@heygen/liveavatar-web-sdk';
import toast from 'react-hot-toast';
import type { Dealership, UIChatMessage } from '../types';

export type ChatMode = 'training' | 'roleplay';
export type VoiceState = 'idle' | 'connecting' | 'listening' | 'recording' | 'processing' | 'speaking';

const generateMessageId = () => `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

export function useVoiceChat() {
  const { user } = useAuth();
  
  // Core state
  const [mode, setMode] = useState<ChatMode>('training');
  const [voiceState, setVoiceState] = useState<VoiceState>('idle');
  const [textInput, setTextInput] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [chatMessages, setChatMessages] = useState<UIChatMessage[]>([]);
  
  // Dealership state
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
  const avatarSessionRef = useRef<LiveAvatarSession | null>(null);
  const avatarVideoRef = useRef<HTMLVideoElement | null>(null);
  const avatarEnabledRef = useRef(avatarEnabled);
  
  const stateRefs = useRef({ mode, isListening, voiceState, transcript });
  
  useEffect(() => {
    stateRefs.current = { mode, isListening, voiceState, transcript };
  }, [mode, isListening, voiceState, transcript]);
  
  useEffect(() => {
    avatarEnabledRef.current = avatarEnabled;
  }, [avatarEnabled]);

  // Load dealerships
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

  // Avatar initialization
  const initializeAvatar = useCallback(async () => {
    if (avatarSessionRef.current) return;
    
    setIsAvatarLoading(true);
    try {
      const { session_token } = await avatarApi.createSession();
      const session = new LiveAvatarSession(session_token);
      avatarSessionRef.current = session;
      
      session.on(SessionEvent.SESSION_STATE_CHANGED, (state: SessionState) => {
        setAvatarState(state);
        if (state === SessionState.CONNECTED) {
          setIsAvatarLoading(false);
        }
      });
      
      session.on(AgentEventsEnum.AVATAR_SPEAK_STARTED, () => {
        setVoiceState('speaking');
      });
      
      session.on(AgentEventsEnum.AVATAR_SPEAK_ENDED, () => {
        setVoiceState(stateRefs.current.isListening ? 'listening' : 'idle');
      });
      
      session.on(SessionEvent.SESSION_STREAM_READY, () => {
        if (avatarVideoRef.current) {
          session.attach(avatarVideoRef.current);
        }
      });
      
      await session.start();
      
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

  const handleVideoRef = useCallback((element: HTMLVideoElement | null) => {
    avatarVideoRef.current = element;
    if (element && avatarSessionRef.current && avatarState === SessionState.CONNECTED) {
      avatarSessionRef.current.attach(element);
    }
  }, [avatarState]);

  const avatarSpeak = useCallback((text: string) => {
    console.log('avatarSpeak called:', { text: text.substring(0, 50), hasSession: !!avatarSessionRef.current, avatarState });
    if (avatarSessionRef.current) {
      try {
        console.log('Calling avatar.repeat()');
        avatarSessionRef.current.repeat(text);
      } catch (e) {
        console.error('Error making avatar speak:', e);
      }
    } else {
      console.warn('Avatar session not available');
    }
  }, [avatarState]);

  // Message helpers
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

  // WebSocket
  const handleWsMessage = useCallback((event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data);

      switch (data.type) {
        case 'ready':
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
            
            if (avatarEnabledRef.current && avatarSessionRef.current) {
              try {
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

  const connectWebSocket = useCallback(() => {
    if (!user?.id || wsRef.current?.readyState === WebSocket.OPEN) return;
    if (wsRef.current?.readyState === WebSocket.CONNECTING) return;

    // Get access token for WebSocket authentication
    const accessToken = localStorage.getItem('access_token');
    if (!accessToken) {
      toast.error('Authentication required');
      return;
    }

    setVoiceState('connecting');
    // Pass JWT token as query parameter for WebSocket authentication
    const wsUrl = `${getWsBaseUrl()}/voice/ws/live/${user.id}?token=${encodeURIComponent(accessToken)}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({ type: 'init', mode: stateRefs.current.mode }));
    };
    ws.onmessage = handleWsMessage;
    ws.onclose = (event) => {
      setIsConnected(false);
      setIsListening(false);
      wsRef.current = null;
      stopAudioStream();
      
      // Handle authentication errors
      if (event.code === 4001) {
        toast.error('WebSocket authentication failed');
      } else if (event.code === 4003) {
        toast.error('Access denied');
      }
    };
    ws.onerror = () => {
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

  // Audio stream
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
      const SILENCE_THRESHOLD = 0.02;
      const SILENCE_FRAMES_NEEDED = 10; // ~200ms of silence

      processor.onaudioprocess = (e) => {
        if (wsRef.current?.readyState !== WebSocket.OPEN) {
          return;
        }

        const inputData = e.inputBuffer.getChannelData(0);
        
        // Calculate RMS to detect speech
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

        // Send as base64 encoded JSON message (same protocol as VoiceChat.tsx)
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
  }, [isConnected, connectWebSocket, interruptResponse]);

  const stopListening = useCallback(() => {
    stopAudioStream();
    setIsListening(false);
    setVoiceState('idle');
  }, [stopAudioStream]);

  // Send text message
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
      
      // Use ref for avatarEnabled to get current value
      if (avatarEnabledRef.current && avatarSessionRef.current && avatarState === SessionState.CONNECTED) {
        finalizeAssistantMessage(assistantMsgId, chatResponse.response);
        avatarSpeak(chatResponse.response);
      } else {
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
  }, [textInput, voiceState, mode, dealershipId, addUserMessage, addAssistantMessage, finalizeAssistantMessage, playAudio, avatarState, avatarSpeak]);

  // Voice message
  const handleVoiceMessage = useCallback(async (audioBlob: Blob) => {
    setVoiceState('processing');
    
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
      
      if (response.user_transcript) {
        setChatMessages(prev => prev.map(msg => 
          msg.id === userMsgId ? { ...msg, content: response.user_transcript } : msg
        ));
      }
      
      // Use ref for avatarEnabled to get current value
      if (avatarEnabledRef.current && avatarSessionRef.current && avatarState === SessionState.CONNECTED && response.response_text) {
        finalizeAssistantMessage(assistantMsgId, response.response_text);
        avatarSpeak(response.response_text);
      } else {
        if (response.response_text) {
          finalizeAssistantMessage(assistantMsgId, response.response_text, response.response_audio_base64);
        }
        playAudio(response.response_audio_base64);
      }
    } catch (error: unknown) {
      const err = error as { response?: { data?: { error?: { message?: string } } } };
      toast.error(err.response?.data?.error?.message || 'Failed to process audio');
      setChatMessages(prev => prev.filter(m => m.id !== assistantMsgId && m.id !== userMsgId));
      setVoiceState('idle');
    }
  }, [mode, dealershipId, addUserMessage, addAssistantMessage, finalizeAssistantMessage, playAudio, avatarState, avatarSpeak]);

  // Reset
  const resetConversation = useCallback(() => {
    stopAudio();
    setTranscript('');
    setInterimTranscript('');
    setChatMessages([]);
    pendingMessageIdRef.current = null;
    sessionIdRef.current = null;
    wsRef.current?.send(JSON.stringify({ type: 'clear' }));
  }, [stopAudio]);

  // Effects
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

  useEffect(() => {
    if (isConnected && wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'init', mode }));
    }
  }, [mode, isConnected]);

  return {
    // State
    user,
    mode,
    setMode,
    voiceState,
    textInput,
    setTextInput,
    isConnected,
    transcript,
    interimTranscript,
    isListening,
    chatMessages,
    dealerships,
    selectedDealershipId,
    setSelectedDealershipId,
    isLoadingDealerships,
    avatarEnabled,
    setAvatarEnabled,
    avatarState,
    isAvatarLoading,
    isSuperAdmin,
    dealershipId,
    
    // Actions
    initializeAvatar,
    cleanupAvatar,
    handleVideoRef,
    avatarSpeak,
    sendTextMessage,
    handleVoiceMessage,
    resetConversation,
    startListening,
    stopListening,
    stopAudio,
    playAudio,
  };
}
