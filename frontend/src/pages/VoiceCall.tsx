/**
 * VoiceCall - Google Meet style video call with HeyGen Avatar
 * 
 * Flow:
 * 1. User speaks → Browser Speech Recognition → Text
 * 2. Text → Backend chat API → LLM response
 * 3. LLM response → HeyGen repeat() → Avatar speaks
 * 
 * Note: Mic is paused while Adam is speaking (red icon indicates not listening)
 * User should wait for Adam to finish before speaking.
 * 
 * Uses FULL mode with repeat(): Avatar speaks exactly what we tell it.
 * repeat() uses HeyGen's built-in TTS - no AI agent involved.
 */

import { useEffect, useState, useRef, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { avatarApi, dealershipApi, chatApi } from '../services/api';
import { 
  LiveAvatarSession, 
  SessionState, 
  SessionEvent,
  AgentEventsEnum,
} from '@heygen/liveavatar-web-sdk';
import { 
  Mic, MicOff, PhoneOff, Phone, Volume2, VolumeX, Loader2, 
  User, Building2
} from 'lucide-react';
import clsx from 'clsx';
import toast from 'react-hot-toast';
import type { Dealership } from '../types';

// Browser Speech Recognition types
interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
  resultIndex: number;
}

interface SpeechRecognitionResultList {
  length: number;
  item(index: number): SpeechRecognitionResult;
  [index: number]: SpeechRecognitionResult;
}

interface SpeechRecognitionResult {
  isFinal: boolean;
  length: number;
  item(index: number): SpeechRecognitionAlternative;
  [index: number]: SpeechRecognitionAlternative;
}

interface SpeechRecognitionAlternative {
  transcript: string;
  confidence: number;
}

interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onend: (() => void) | null;
  onerror: ((event: Event) => void) | null;
  onstart: (() => void) | null;
  onspeechstart: (() => void) | null;
  onspeechend: (() => void) | null;
  onaudiostart: (() => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}

declare global {
  interface Window {
    SpeechRecognition: new () => SpeechRecognition;
    webkitSpeechRecognition: new () => SpeechRecognition;
  }
}

type CallState = 'idle' | 'connecting' | 'connected' | 'error';
type SpeakingState = 'none' | 'user' | 'avatar';
type ConversationMessage = { role: 'user' | 'assistant'; content: string };

export default function VoiceCall() {
  const { user } = useAuth();
  
  // Call state
  const [callState, setCallState] = useState<CallState>('idle');
  const [speakingState, setSpeakingState] = useState<SpeakingState>('none');
  const [isMicMuted, setIsMicMuted] = useState(false);
  const [isAudioMuted, setIsAudioMuted] = useState(false); // Start with audio on
  
  // Transcription
  const [userTranscript, setUserTranscript] = useState('');
  const [_avatarTranscript, setAvatarTranscript] = useState(''); // Kept for HeyGen events
  const [isProcessing, setIsProcessing] = useState(false);
  
  // Conversation state
  const [chatSessionId, setChatSessionId] = useState<string | undefined>();
  const conversationHistoryRef = useRef<ConversationMessage[]>([]);
  const [mode, setMode] = useState<'training' | 'roleplay'>('training');
  
  // Dealership (for super admin)
  const [dealerships, setDealerships] = useState<Dealership[]>([]);
  const [selectedDealershipId, setSelectedDealershipId] = useState<number | null>(null);
  const [isLoadingDealerships, setIsLoadingDealerships] = useState(false);
  const [dealershipsLoaded, setDealershipsLoaded] = useState(false);
  
  const isSuperAdmin = user?.role === 'super_admin';
  
  // Refs
  const sessionRef = useRef<LiveAvatarSession | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamReadyRef = useRef<boolean>(false);
  const userTranscriptTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const avatarTranscriptTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const selectedDealershipIdRef = useRef<number | null>(null);
  const isAvatarSpeakingRef = useRef<boolean>(false);
  const isProcessingRef = useRef<boolean>(false);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const isListeningRef = useRef<boolean>(false);
  const lastProcessedTranscriptRef = useRef<string>(''); // Prevent duplicate processing
  const pendingResponseRef = useRef<string | null>(null); // Track pending avatar response
  const speakEndTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null); // Debounce speak end
  
  // Keep dealership ref in sync with state
  useEffect(() => {
    selectedDealershipIdRef.current = selectedDealershipId;
  }, [selectedDealershipId]);
  
  // Callback ref to attach stream when video element is available
  const handleVideoRef = useCallback((element: HTMLVideoElement | null) => {
    videoRef.current = element;
    // If stream is ready and we just got the video element, attach it
    if (element && sessionRef.current && streamReadyRef.current) {
      console.log('Attaching stream to video element (from ref callback)');
      sessionRef.current.attach(element);
    }
  }, []);

  // Process user transcription through backend and make avatar speak
  const processUserSpeech = useCallback(async (transcript: string) => {
    const trimmedTranscript = transcript.trim();
    
    // Don't process if empty or no session
    if (!trimmedTranscript || !sessionRef.current) return;
    
    // Don't process if already processing
    if (isProcessingRef.current) {
      console.log('Skipping - already processing');
      return;
    }
    
    // Prevent duplicate processing of the same transcript
    if (trimmedTranscript === lastProcessedTranscriptRef.current) {
      console.log('Skipping - duplicate transcript');
      return;
    }
    
    // Determine dealership ID
    const dealershipId = isSuperAdmin ? selectedDealershipIdRef.current : user?.dealership_id;
    
    // Super admin must have a dealership selected
    if (isSuperAdmin && !dealershipId) {
      toast.error('Please select a dealership first');
      return;
    }
    
    // Set processing flag and remember this transcript
    isProcessingRef.current = true;
    lastProcessedTranscriptRef.current = trimmedTranscript;
    
    // Stop recognition while processing to prevent picking up stray audio
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {
        // Ignore - may already be stopped
      }
    }
    
    console.log('Processing user speech:', trimmedTranscript);
    setIsProcessing(true);
    setSpeakingState('none');
    
    try {
      // Add user message to history
      conversationHistoryRef.current.push({ role: 'user', content: trimmedTranscript });
      
      // Send to backend
      const response = await chatApi.send({
        message: trimmedTranscript,
        mode,
        session_id: chatSessionId,
        conversation_history: conversationHistoryRef.current,
        dealership_id: dealershipId ?? undefined,
      });
      
      console.log('Backend response:', response);
      
      // Update session ID
      if (response.session_id) {
        setChatSessionId(response.session_id);
      }
      
      // Add assistant response to history
      conversationHistoryRef.current.push({ role: 'assistant', content: response.response });
      
      // FULL mode: Use repeat() to make avatar speak text (built-in TTS)
      if (sessionRef.current && response.response) {
        console.log('Making avatar speak with repeat():', response.response);
        
        // Track the full response - we'll use this to know when avatar is truly done
        // HeyGen may fire multiple SPEAK_STARTED/ENDED events for long text
        pendingResponseRef.current = response.response;
        
        // repeat() makes avatar speak the exact text using built-in TTS
        // This does NOT go through HeyGen's AI - it just speaks what we tell it
        sessionRef.current.repeat(response.response);
      } else {
        // No response or no session - reset state
        isAvatarSpeakingRef.current = false;
        isProcessingRef.current = false;
        pendingResponseRef.current = null;
        setSpeakingState('none');
        setIsProcessing(false);
      }
      
    } catch (error) {
      console.error('Error processing speech:', error);
      toast.error('Failed to process your message');
      isAvatarSpeakingRef.current = false;
      isProcessingRef.current = false;
      setSpeakingState('none');
      setIsProcessing(false);
    }
  }, [chatSessionId, isSuperAdmin, user?.dealership_id, mode]);

  // Load dealerships for super admin
  useEffect(() => {
    if (isSuperAdmin && !dealershipsLoaded) {
      setIsLoadingDealerships(true);
      dealershipApi.list()
        .then((data) => {
          setDealerships(data);
          setDealershipsLoaded(true);
          if (data.length > 0) {
            setSelectedDealershipId(data[0].id);
          }
        })
        .catch((error) => {
          console.error('Failed to load dealerships:', error);
          toast.error('Failed to load dealerships');
        })
        .finally(() => {
          setIsLoadingDealerships(false);
        });
    }
  }, [isSuperAdmin, dealershipsLoaded]);

  // Initialize browser Speech Recognition
  const initSpeechRecognition = useCallback(() => {
    const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognitionAPI) {
      toast.error('Speech recognition not supported in this browser');
      return null;
    }
    
    const recognition = new SpeechRecognitionAPI();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';
    
    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let finalTranscript = '';
      let interimTranscript = '';
      
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          finalTranscript += result[0].transcript;
        } else {
          interimTranscript += result[0].transcript;
        }
      }
      
      // Show interim transcript - user is speaking
      if (interimTranscript) {
        setUserTranscript(interimTranscript);
        setSpeakingState('user');
      }
      
      // Process final transcript only - ignore if it matches last processed
      if (finalTranscript) {
        const trimmed = finalTranscript.trim();
        
        // Skip if empty or duplicate
        if (!trimmed || trimmed === lastProcessedTranscriptRef.current) {
          console.log('Skipping empty or duplicate final transcript');
          return;
        }
        
        // Skip if already processing
        if (isProcessingRef.current) {
          console.log('Skipping - already processing');
          return;
        }
        
        console.log('Final transcript:', trimmed);
        setUserTranscript(trimmed);
        setSpeakingState('none');
        processUserSpeech(trimmed);
      }
    };
    
    recognition.onend = () => {
      console.log('Speech recognition ended');
      // Only restart if NOT processing and NOT avatar speaking
      // If avatar is speaking or we're processing, the SPEAK_ENDED handler will restart us
      if (isListeningRef.current && !isProcessingRef.current && !isAvatarSpeakingRef.current && !pendingResponseRef.current) {
        setTimeout(() => {
          if (isListeningRef.current && !isProcessingRef.current && !isAvatarSpeakingRef.current && !pendingResponseRef.current && recognitionRef.current) {
            try {
              recognitionRef.current.start();
              console.log('Speech recognition restarted (from onend)');
            } catch (e) {
              console.log('Could not restart recognition:', e);
            }
          }
        }, 100);
      } else {
        console.log('Not restarting recognition - processing:', isProcessingRef.current, 'avatarSpeaking:', isAvatarSpeakingRef.current, 'pendingResponse:', !!pendingResponseRef.current);
      }
    };
    
    // Fired when speech is first detected
    recognition.onspeechstart = () => {
      console.log('Speech detected');
      // Show that user is speaking (only if not processing)
      if (!isProcessingRef.current && !isAvatarSpeakingRef.current) {
        setSpeakingState('user');
      }
    };
    
    recognition.onspeechend = () => {
      console.log('Speech ended');
    };
    
    recognition.onerror = (event: Event & { error?: string }) => {
      console.error('Speech recognition error:', event);
      // Don't treat 'no-speech' or 'aborted' as fatal errors - just restart
      const errorType = event.error || '';
      if (errorType === 'no-speech' || errorType === 'aborted') {
        console.log('Non-fatal speech error, will restart automatically');
      }
    };
    
    return recognition;
  }, [processUserSpeech]);

  // Start listening for speech
  const startListening = useCallback(() => {
    if (!recognitionRef.current) {
      recognitionRef.current = initSpeechRecognition();
    }
    if (recognitionRef.current && !isListeningRef.current) {
      try {
        recognitionRef.current.start();
        isListeningRef.current = true;
        setIsMicMuted(false);
        console.log('Started listening');
      } catch (e) {
        console.error('Failed to start listening:', e);
      }
    }
  }, [initSpeechRecognition]);

  // Stop listening for speech
  const stopListening = useCallback(() => {
    if (recognitionRef.current && isListeningRef.current) {
      recognitionRef.current.stop();
      isListeningRef.current = false;
      setIsMicMuted(true);
      console.log('Stopped listening');
    }
  }, []);

  // Start the call
  const startCall = useCallback(async () => {
    if (sessionRef.current) return;
    
    setCallState('connecting');
    
    try {
      // Generate a unique session ID for RAG pre-warming
      const ragSessionId = `voicecall_${user?.id}_${Date.now()}`;
      setChatSessionId(ragSessionId);
      
      // Determine dealership ID for pre-warming
      const dealershipId = isSuperAdmin ? selectedDealershipIdRef.current : user?.dealership_id;
      
      // Start pre-warming RAG context in parallel with avatar session setup
      // This reduces latency on the first voice query
      const prewarmPromise = dealershipId 
        ? chatApi.prewarmSession(ragSessionId, dealershipId).then((result) => {
            console.log('RAG pre-warm complete:', result);
          }).catch((error) => {
            console.warn('RAG pre-warm failed (non-critical):', error);
          })
        : Promise.resolve();
      
      // Get session token (LITE mode - TTS only)
      const { session_token } = await avatarApi.createSession();
      
      // Create session
      const session = new LiveAvatarSession(session_token);
      sessionRef.current = session;
      
      // Session state events
      session.on(SessionEvent.SESSION_STATE_CHANGED, (state: SessionState) => {
        console.log('Session state:', state);
        if (state === SessionState.CONNECTED) {
          setCallState('connected');
          // Start listening for speech when connected
          startListening();
        } else if (state === SessionState.DISCONNECTED) {
          setCallState('idle');
          stopListening();
        }
      });
      
      // Stream ready - attach video
      session.on(SessionEvent.SESSION_STREAM_READY, () => {
        console.log('Stream ready');
        streamReadyRef.current = true;
        if (videoRef.current && sessionRef.current) {
          console.log('Attaching stream to video element (from event)');
          sessionRef.current.attach(videoRef.current);
        }
      });
      
      // Avatar speaking events - track when avatar starts/stops speaking
      // IMPORTANT: HeyGen fires multiple SPEAK_STARTED/ENDED events for long text
      // We debounce SPEAK_ENDED to avoid restarting mic between chunks
      session.on(AgentEventsEnum.AVATAR_SPEAK_STARTED, () => {
        console.log('Avatar started speaking');
        isAvatarSpeakingRef.current = true;
        setSpeakingState('avatar');
        
        // Cancel any pending "speak ended" handler - avatar is still talking
        if (speakEndTimeoutRef.current) {
          clearTimeout(speakEndTimeoutRef.current);
          speakEndTimeoutRef.current = null;
          console.log('Cancelled speak-end timeout - avatar still speaking');
        }
      });
      
      session.on(AgentEventsEnum.AVATAR_SPEAK_ENDED, () => {
        console.log('Avatar speak chunk ended');
        
        // Don't immediately assume avatar is done - wait to see if another chunk starts
        // Use a longer debounce to account for pauses between sentences
        if (speakEndTimeoutRef.current) {
          clearTimeout(speakEndTimeoutRef.current);
        }
        
        speakEndTimeoutRef.current = setTimeout(() => {
          console.log('Avatar fully stopped speaking (debounced)');
          isAvatarSpeakingRef.current = false;
          isProcessingRef.current = false;
          pendingResponseRef.current = null;
          setSpeakingState('none');
          setIsProcessing(false);
          setUserTranscript(''); // Clear user transcript for next input
          
          // Clear avatar transcript after a delay
          setTimeout(() => setAvatarTranscript(''), 3000);
          
          // Restart speech recognition after additional delay
          setTimeout(() => {
            console.log('Re-enabling speech recognition after avatar finished');
            lastProcessedTranscriptRef.current = ''; // Allow new transcripts
            
            if (recognitionRef.current && isListeningRef.current) {
              try {
                recognitionRef.current.start();
                console.log('Speech recognition started after avatar finished');
              } catch (e) {
                console.log('Could not start recognition:', e);
              }
            }
          }, 500); // Additional 500ms after debounce
        }, 1500); // 1.5 second debounce - wait to see if more speech is coming
      });
      
      // Avatar transcription - what the avatar is saying
      session.on(AgentEventsEnum.AVATAR_TRANSCRIPTION, (data: { text: string }) => {
        console.log('Avatar transcription:', data.text);
        setAvatarTranscript(data.text);
      });
      
      // Start session
      await session.start();
      
      // Attach video
      if (videoRef.current) {
        session.attach(videoRef.current);
      }
      
      // Wait for pre-warm to complete (but don't block on it)
      await prewarmPromise;
      
      toast.success('Call connected');
      
    } catch (error) {
      console.error('Failed to start call:', error);
      toast.error('Failed to connect call');
      setCallState('error');
    }
  }, [startListening, stopListening, user?.id, user?.dealership_id, isSuperAdmin]);

  // End the call
  const endCall = useCallback(() => {
    // Stop speech recognition
    stopListening();
    
    // Clear any pending speak-end timeout
    if (speakEndTimeoutRef.current) {
      clearTimeout(speakEndTimeoutRef.current);
      speakEndTimeoutRef.current = null;
    }
    
    if (sessionRef.current) {
      try {
        sessionRef.current.stop();
      } catch (e) {
        console.error('Error ending call:', e);
      }
      sessionRef.current = null;
    }
    streamReadyRef.current = false;
    isAvatarSpeakingRef.current = false;
    isProcessingRef.current = false;
    pendingResponseRef.current = null;
    lastProcessedTranscriptRef.current = '';
    setCallState('idle');
    setSpeakingState('none');
    setUserTranscript('');
    setAvatarTranscript('');
    setIsProcessing(false);
    
    // Clear RAG session context (non-blocking)
    if (chatSessionId) {
      chatApi.clearSessionContext(chatSessionId).catch((error) => {
        console.warn('Failed to clear session context:', error);
      });
    }
    
    // Reset conversation for next call
    setChatSessionId(undefined);
    conversationHistoryRef.current = [];
  }, [stopListening, chatSessionId]);

  // Handle dealership change - end current call and reset conversation
  const handleDealershipChange = useCallback((newDealershipId: number) => {
    if (newDealershipId === selectedDealershipId) return;
    
    // End current call if connected
    if (callState === 'connected' || callState === 'connecting') {
      endCall();
    }
    
    // Reset conversation state
    setChatSessionId(undefined);
    conversationHistoryRef.current = [];
    
    // Set new dealership
    setSelectedDealershipId(newDealershipId);
    
    toast.success('Dealership changed. Start a new call to continue.');
  }, [selectedDealershipId, callState, endCall]);

  // Toggle microphone (start/stop listening)
  const toggleMic = useCallback(() => {
    if (isMicMuted) {
      startListening();
    } else {
      stopListening();
    }
  }, [isMicMuted, startListening, stopListening]);

  // Toggle audio (speaker)
  const toggleAudio = useCallback(() => {
    if (videoRef.current) {
      videoRef.current.muted = !videoRef.current.muted;
      setIsAudioMuted(videoRef.current.muted);
    }
  }, []);

  // Cleanup on unmount only
  useEffect(() => {
    return () => {
      // Stop speech recognition
      if (recognitionRef.current && isListeningRef.current) {
        recognitionRef.current.stop();
        isListeningRef.current = false;
      }
      
      // Stop HeyGen session
      if (sessionRef.current) {
        try {
          sessionRef.current.stop();
        } catch (e) {
          console.error('Error stopping session on unmount:', e);
        }
      }
      
      // Clear timeouts
      if (userTranscriptTimeoutRef.current) clearTimeout(userTranscriptTimeoutRef.current);
      if (avatarTranscriptTimeoutRef.current) clearTimeout(avatarTranscriptTimeoutRef.current);
      if (speakEndTimeoutRef.current) clearTimeout(speakEndTimeoutRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Empty deps - only run on unmount

  // Access check for non-super admin
  if (!isSuperAdmin && !user?.dealership_id) {
    return (
      <div className="fixed inset-0 top-16 lg:top-0 lg:left-64 bg-gray-100 flex items-center justify-center">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 max-w-md text-center">
          <Building2 className="w-12 h-12 text-yellow-600 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-yellow-800 mb-2">No Dealership Assigned</h3>
          <p className="text-yellow-700">You are not associated with a dealership. Please contact your administrator.</p>
        </div>
      </div>
    );
  }

  // Loading dealerships for super admin
  if (isSuperAdmin && isLoadingDealerships) {
    return (
      <div className="fixed inset-0 top-16 lg:top-0 lg:left-64 bg-gray-100 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-12 h-12 text-primary-600 animate-spin" />
          <p className="text-gray-600 text-lg">Loading dealerships...</p>
        </div>
      </div>
    );
  }

  // No dealerships found for super admin
  if (isSuperAdmin && dealershipsLoaded && dealerships.length === 0) {
    return (
      <div className="fixed inset-0 top-16 lg:top-0 lg:left-64 bg-gray-100 flex items-center justify-center">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 max-w-md text-center">
          <Building2 className="w-12 h-12 text-yellow-600 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-yellow-800 mb-2">No Dealerships Found</h3>
          <p className="text-yellow-700">Please create a dealership first before using call.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 top-16 lg:top-0 lg:left-64 bg-gray-100 flex flex-col">
      {/* Main video area */}
      <div className="flex-1 relative flex items-center justify-center p-4">
        {/* Avatar video (main) */}
        <div className={clsx(
          'relative w-full max-w-4xl aspect-video bg-white rounded-2xl overflow-hidden shadow-xl border border-gray-200 transition-all duration-300',
          speakingState === 'avatar' && 'ring-4 ring-green-500'
        )}>
          {/* Video element - always rendered but hidden when not connected */}
          <video
            ref={handleVideoRef}
            autoPlay
            playsInline
            muted={isAudioMuted}
            className={clsx(
              'w-full h-full object-cover',
              callState !== 'connected' && 'hidden'
            )}
          />
          
          {/* Connecting overlay */}
          {callState === 'connecting' && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-50">
              <Loader2 className="w-16 h-16 text-primary-600 animate-spin mb-4" />
              <p className="text-gray-700 text-lg">Connecting...</p>
            </div>
          )}
          
          {/* Idle/Error overlay */}
          {(callState === 'idle' || callState === 'error') && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-50">
              <div className="w-24 h-24 bg-primary-100 rounded-full flex items-center justify-center mb-4">
                <User className="w-12 h-12 text-primary-600" />
              </div>
              <p className="text-gray-800 text-lg mb-2">Adam - AI F&I Trainer</p>
              <p className="text-gray-500 text-sm mb-6">Ready to start call</p>
              
              {/* Mode Selection */}
              <div className="mb-6 flex flex-col items-center gap-2">
                <label className="text-gray-600 text-sm font-medium">Select Mode</label>
                <div className="flex bg-gray-100 rounded-full p-1">
                  <button
                    onClick={() => setMode('training')}
                    className={clsx(
                      'px-6 py-2 text-sm font-medium rounded-full transition-colors',
                      mode === 'training' 
                        ? 'bg-white text-primary-600 shadow-sm' 
                        : 'text-gray-500 hover:text-gray-700'
                    )}
                  >
                    Training
                  </button>
                  <button
                    onClick={() => setMode('roleplay')}
                    className={clsx(
                      'px-6 py-2 text-sm font-medium rounded-full transition-colors',
                      mode === 'roleplay' 
                        ? 'bg-white text-primary-600 shadow-sm' 
                        : 'text-gray-500 hover:text-gray-700'
                    )}
                  >
                    Role-Play
                  </button>
                </div>
                <p className="text-gray-400 text-xs mt-1">
                  {mode === 'training' 
                    ? 'Adam will train you on F&I products' 
                    : 'Practice with a simulated customer'}
                </p>
              </div>
              
              <button
                onClick={startCall}
                className="px-8 py-4 bg-green-600 text-white rounded-full font-medium hover:bg-green-700 transition-colors flex items-center gap-3 text-lg"
              >
                <Phone className="w-6 h-6" />
                Start Call
              </button>
            </div>
          )}
          
          {/* Avatar name badge */}
          {callState === 'connected' && (
            <div className="absolute bottom-4 left-4 px-3 py-1.5 bg-white/90 backdrop-blur-sm rounded-lg flex items-center gap-2 shadow-md border border-gray-200">
              {speakingState === 'avatar' && (
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              )}
              {isProcessing && (
                <Loader2 className="w-3 h-3 text-primary-600 animate-spin" />
              )}
              <span className="text-gray-800 text-sm font-medium">
                {isProcessing ? 'Adam is thinking...' : 'Adam'}
              </span>
            </div>
          )}
          
          {/* Unmute audio prompt */}
          {callState === 'connected' && isAudioMuted && (
            <button
              onClick={toggleAudio}
              className="absolute top-4 right-4 px-4 py-2 bg-red-500 text-white rounded-full text-sm font-medium flex items-center gap-2 hover:bg-red-600 transition-colors animate-pulse"
            >
              <VolumeX className="w-4 h-4" />
              Click to hear audio
            </button>
          )}
        </div>
        
        {/* User indicator (picture-in-picture style) */}
        <div className={clsx(
          'absolute bottom-8 right-8 w-48 h-36 bg-white rounded-xl overflow-hidden shadow-lg border-2 transition-all duration-300',
          speakingState === 'user' ? 'border-green-500 scale-105' : 'border-gray-200'
        )}>
          <div className="w-full h-full flex flex-col items-center justify-center">
            <div className={clsx(
              'w-16 h-16 rounded-full flex items-center justify-center mb-2 transition-colors',
              speakingState === 'user' ? 'bg-green-500' : 'bg-gray-100'
            )}>
              {speakingState === 'user' ? (
                <Volume2 className="w-8 h-8 text-white animate-pulse" />
              ) : (
                <User className="w-8 h-8 text-gray-500" />
              )}
            </div>
            <span className="text-gray-800 text-xs font-medium">You</span>
            {speakingState === 'user' && (
              <span className="text-green-600 text-xs mt-1">Speaking...</span>
            )}
          </div>
          
          {/* Mic indicator */}
          {isMicMuted && (
            <div className="absolute bottom-2 right-2 w-6 h-6 bg-red-500 rounded-full flex items-center justify-center">
              <MicOff className="w-3 h-3 text-white" />
            </div>
          )}
        </div>
        
        {/* Dealership selector (top left) */}
        {isSuperAdmin && dealerships.length > 0 && (
          <div className="absolute top-4 left-4 flex items-center gap-2 bg-white/95 backdrop-blur-sm rounded-lg px-3 py-2 shadow-md border border-gray-200">
            <Building2 className="w-4 h-4 text-primary-600" />
            <select
              value={selectedDealershipId || ''}
              onChange={(e) => handleDealershipChange(Number(e.target.value))}
              className="px-2 py-1 bg-transparent text-gray-800 text-sm font-medium border-none focus:ring-0 cursor-pointer min-w-[150px]"
            >
              {dealerships.map((d) => (
                <option key={d.id} value={d.id} className="bg-white">{d.name}</option>
              ))}
            </select>
          </div>
        )}
      </div>
      
      {/* Captions - show only user transcript */}
      <div className="h-16 flex items-center justify-center px-4">
        {userTranscript && (
          <div className="max-w-2xl w-full">
            <p className="text-gray-800 text-lg text-center">
              <span className="text-blue-600 font-medium">You: </span>
              {userTranscript}
            </p>
          </div>
        )}
      </div>
      
      {/* Bottom controls */}
      <div className="h-24 bg-white border-t border-gray-200 flex items-center justify-center gap-4 px-4">
        {/* Mic toggle - shows red when not listening (avatar speaking or processing) */}
        <button
          onClick={toggleMic}
          disabled={callState !== 'connected' || speakingState === 'avatar' || isProcessing}
          className={clsx(
            'w-14 h-14 rounded-full flex items-center justify-center transition-all shadow-md',
            // Red when muted OR when avatar is speaking/processing (not listening)
            (isMicMuted || speakingState === 'avatar' || isProcessing)
              ? 'bg-red-500 text-white' 
              : 'bg-gray-100 hover:bg-gray-200 text-gray-700',
            (callState !== 'connected' || speakingState === 'avatar' || isProcessing) && 'cursor-not-allowed'
          )}
          title={
            speakingState === 'avatar' 
              ? 'Wait for Adam to finish speaking' 
              : isProcessing 
                ? 'Processing your message...'
                : isMicMuted 
                  ? 'Unmute microphone' 
                  : 'Mute microphone'
          }
        >
          {(isMicMuted || speakingState === 'avatar' || isProcessing) ? (
            <MicOff className="w-6 h-6" />
          ) : (
            <Mic className="w-6 h-6" />
          )}
        </button>
        
        {/* Audio toggle */}
        <button
          onClick={toggleAudio}
          disabled={callState !== 'connected'}
          className={clsx(
            'w-14 h-14 rounded-full flex items-center justify-center transition-all shadow-md',
            isAudioMuted 
              ? 'bg-red-500 hover:bg-red-600 text-white' 
              : 'bg-gray-100 hover:bg-gray-200 text-gray-700',
            callState !== 'connected' && 'opacity-50 cursor-not-allowed'
          )}
          title={isAudioMuted ? 'Unmute audio' : 'Mute audio'}
        >
          {isAudioMuted ? (
            <VolumeX className="w-6 h-6" />
          ) : (
            <Volume2 className="w-6 h-6" />
          )}
        </button>
        
        {/* End call / Start call */}
        {callState === 'connected' ? (
          <button
            onClick={endCall}
            className="w-14 h-14 rounded-full bg-red-500 hover:bg-red-600 flex items-center justify-center transition-all shadow-md"
            title="End call"
          >
            <PhoneOff className="w-6 h-6 text-white" />
          </button>
        ) : callState === 'idle' || callState === 'error' ? (
          <button
            onClick={startCall}
            className="w-14 h-14 rounded-full bg-green-500 hover:bg-green-600 flex items-center justify-center transition-all shadow-md"
            title="Start call"
          >
            <Phone className="w-6 h-6 text-white" />
          </button>
        ) : (
          <button
            disabled
            className="w-14 h-14 rounded-full bg-gray-200 flex items-center justify-center opacity-50 cursor-not-allowed"
          >
            <Loader2 className="w-6 h-6 text-gray-500 animate-spin" />
          </button>
        )}
      </div>
    </div>
  );
}
