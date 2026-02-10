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
import { useSearchParams } from 'react-router-dom';
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
  User, Building2, StopCircle
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
  const [searchParams] = useSearchParams();
  
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
  
  // Get initial mode from URL query parameter or default to 'training'
  const initialMode = searchParams.get('mode') === 'roleplay' ? 'roleplay' : 'training';
  const [mode, setMode] = useState<'training' | 'roleplay'>(initialMode);
  
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
  const currentRequestIdRef = useRef<number>(0); // Track current request to ignore stale responses
  const accumulatedTranscriptRef = useRef<string>(''); // Accumulate user speech across multiple final transcripts
  const processTranscriptTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null); // Debounce processing
  
  // Voice Activity Detection (VAD) refs for interrupt detection
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const micStreamRef = useRef<MediaStream | null>(null);
  const vadIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const consecutiveSpeechFramesRef = useRef<number>(0);
  const consecutiveSilenceFramesRef = useRef<number>(0); // Track silence after speech
  const lastInterimTranscriptRef = useRef<string>(''); // Track last interim for silence processing
  const silenceProcessTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isInterruptingRef = useRef<boolean>(false); // Prevent double interrupts
  const lastInterruptTimeRef = useRef<number>(0); // Cooldown for interrupts
  const isRestartingRecognitionRef = useRef<boolean>(false); // Prevent concurrent restarts
  const VAD_THRESHOLD = 0.015; // RMS threshold for voice detection
  const VAD_FRAMES_TO_INTERRUPT = 5; // ~250ms of speech to trigger interrupt
  const VAD_SILENCE_FRAMES_TO_PROCESS = 30; // ~1.5 seconds of silence to process interim transcript
  const MIN_WORDS_TO_PROCESS = 2; // Minimum words needed to process interim transcript
  const INTERRUPT_COOLDOWN_MS = 1000; // Minimum time between interrupts
  
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
    
    // Prevent processing during an active interrupt
    if (isInterruptingRef.current) {
      console.log('Skipping - interrupt in progress');
      return;
    }
    
    // Prevent concurrent processing (race condition guard)
    if (isProcessingRef.current) {
      console.log('Skipping - already processing a request');
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
    
    // Generate a unique request ID for this request
    const requestId = ++currentRequestIdRef.current;
    console.log(`[Request ${requestId}] Starting processing for: "${trimmedTranscript}"`);
    
    // Set processing flag and remember this transcript
    isProcessingRef.current = true;
    lastProcessedTranscriptRef.current = trimmedTranscript;
    
    // NOTE: We no longer stop recognition during processing
    // This allows the user to interrupt Adam at any time
    // The recognition will continue running and detect interrupts
    
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
      
      // Check if this request is still current (not interrupted)
      if (requestId !== currentRequestIdRef.current) {
        console.log(`[Request ${requestId}] Ignoring stale response - current request is ${currentRequestIdRef.current}`);
        return;
      }
      
      console.log(`[Request ${requestId}] Backend response:`, response);
      
      // Update session ID
      if (response.session_id) {
        setChatSessionId(response.session_id);
      }
      
      // Add assistant response to history
      conversationHistoryRef.current.push({ role: 'assistant', content: response.response });
      
      // Check again if still current before making avatar speak
      if (requestId !== currentRequestIdRef.current) {
        console.log(`[Request ${requestId}] Ignoring - interrupted before avatar speak`);
        return;
      }
      
      // FULL mode: Use repeat() to make avatar speak text (built-in TTS)
      if (sessionRef.current && response.response) {
        console.log(`[Request ${requestId}] Making avatar speak with repeat():`, response.response);
        
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
      // Only handle error if this is still the current request
      if (requestId === currentRequestIdRef.current) {
        console.error(`[Request ${requestId}] Error processing speech:`, error);
        toast.error('Failed to process your message');
        isAvatarSpeakingRef.current = false;
        isProcessingRef.current = false;
        setSpeakingState('none');
        setIsProcessing(false);
      } else {
        console.log(`[Request ${requestId}] Ignoring error - request was interrupted`);
      }
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
      
      // Check if this speech might be Adam's voice being picked up by the mic
      // If Adam is speaking and the recognized text matches part of what Adam is saying, ignore it
      const pendingResponse = pendingResponseRef.current?.toLowerCase() || '';
      const recognizedText = (interimTranscript || finalTranscript).toLowerCase().trim();
      
      // Check if the recognized text is part of Adam's response (echo detection)
      const isEcho = pendingResponse && recognizedText && (
        pendingResponse.includes(recognizedText) || 
        recognizedText.split(' ').some(word => word.length > 3 && pendingResponse.includes(word))
      );
      
      // Debug logging
      console.log('🎤 Speech recognition result:', {
        interim: interimTranscript,
        final: finalTranscript,
        isAvatarSpeaking: isAvatarSpeakingRef.current,
        isProcessing: isProcessingRef.current,
        currentRequestId: currentRequestIdRef.current,
        isEcho: isEcho
      });
      
      // If this is likely Adam's voice being picked up, ignore it
      if (isEcho && isAvatarSpeakingRef.current) {
        console.log('🔇 Ignoring echo - this is Adam\'s voice being picked up');
        return;
      }
      
      // Show interim transcript - user is speaking
      if (interimTranscript) {
        setUserTranscript(interimTranscript);
        setSpeakingState('user');
        
        // Track last interim transcript for silence-based processing
        lastInterimTranscriptRef.current = interimTranscript.trim();
        consecutiveSilenceFramesRef.current = 0; // Reset silence counter when speaking
        
        // INTERRUPT: If Adam is speaking OR processing, and user starts talking, interrupt!
        // But only if this is NOT an echo of Adam's voice
        if ((isAvatarSpeakingRef.current || isProcessingRef.current) && sessionRef.current && !isEcho) {
          console.log('🛑 User interrupting Adam - stopping avatar speech and canceling pending requests');
          
          // Increment request ID to invalidate any pending responses
          currentRequestIdRef.current++;
          console.log(`New request ID after interrupt: ${currentRequestIdRef.current}`);
          
          // Cancel any pending speak-end timeout
          if (speakEndTimeoutRef.current) {
            clearTimeout(speakEndTimeoutRef.current);
            speakEndTimeoutRef.current = null;
          }
          
          // Cancel any pending transcript processing
          if (processTranscriptTimeoutRef.current) {
            clearTimeout(processTranscriptTimeoutRef.current);
            processTranscriptTimeoutRef.current = null;
          }
          
          // Clear accumulated transcript to start fresh
          accumulatedTranscriptRef.current = '';
          
          // Stop the avatar from speaking
          try {
            sessionRef.current.interrupt();
          } catch (e) {
            console.error('Error interrupting avatar:', e);
          }
          
          // Reset state - allow new transcript to be processed
          isAvatarSpeakingRef.current = false;
          isProcessingRef.current = false;
          pendingResponseRef.current = null;
          lastProcessedTranscriptRef.current = ''; // Clear to allow new question
          setIsProcessing(false);
          
          // Don't change speakingState - keep it as 'user' since user is speaking
        }
      }
      
      // Process final transcript only - ignore if it matches last processed
      if (finalTranscript) {
        const trimmed = finalTranscript.trim();
        
        console.log('📝 Final transcript received:', {
          trimmed,
          lastProcessed: lastProcessedTranscriptRef.current,
          isProcessing: isProcessingRef.current,
          isAvatarSpeaking: isAvatarSpeakingRef.current,
          isEcho: isEcho,
          accumulated: accumulatedTranscriptRef.current
        });
        
        // Skip if this is an echo of Adam's voice
        if (isEcho) {
          console.log('🔇 Skipping echo final transcript');
          return;
        }
        
        // Skip if empty
        if (!trimmed) {
          console.log('⏭️ Skipping empty final transcript');
          return;
        }
        
        // Accumulate the transcript (user might be speaking in multiple chunks)
        accumulatedTranscriptRef.current = (accumulatedTranscriptRef.current + ' ' + trimmed).trim();
        setUserTranscript(accumulatedTranscriptRef.current);
        
        // Clear interim transcript since we got a final result
        lastInterimTranscriptRef.current = '';
        
        console.log('📦 Accumulated transcript:', accumulatedTranscriptRef.current);
        
        // Cancel any pending processing timeout
        if (processTranscriptTimeoutRef.current) {
          clearTimeout(processTranscriptTimeoutRef.current);
        }
        
        // Wait for user to stop speaking before processing (debounce)
        processTranscriptTimeoutRef.current = setTimeout(() => {
          const fullTranscript = accumulatedTranscriptRef.current.trim();
          const wordCount = fullTranscript.split(/\s+/).filter(w => w.length > 0).length;
          
          // Skip if duplicate of last processed
          if (fullTranscript === lastProcessedTranscriptRef.current) {
            console.log('⏭️ Skipping duplicate accumulated transcript');
            accumulatedTranscriptRef.current = '';
            return;
          }
          
          // Skip if too few words (likely a fragment)
          if (wordCount < MIN_WORDS_TO_PROCESS) {
            console.log(`⏭️ Skipping short transcript (${wordCount} words): "${fullTranscript}"`);
            accumulatedTranscriptRef.current = '';
            return;
          }
          
          if (fullTranscript) {
            console.log(`✅ Processing accumulated transcript (${wordCount} words):`, fullTranscript);
            setSpeakingState('none');
            processUserSpeech(fullTranscript);
          }
          
          // Clear accumulated transcript
          accumulatedTranscriptRef.current = '';
        }, 1000); // Wait 1 second after last speech to process
      }
    };
    
    recognition.onend = () => {
      console.log('Speech recognition ended');
      // ALWAYS restart speech recognition if we're supposed to be listening
      // This allows user to interrupt Adam at any time
      // But don't restart if we're already restarting (from interrupt handler)
      if (isListeningRef.current && !isRestartingRecognitionRef.current) {
        isRestartingRecognitionRef.current = true;
        setTimeout(() => {
          if (isListeningRef.current && recognitionRef.current) {
            try {
              recognitionRef.current.start();
              console.log('Speech recognition restarted (from onend) - listening for interrupts');
            } catch (e: unknown) {
              if (e instanceof Error && e.name === 'InvalidStateError') {
                console.log('Speech recognition already running (from onend)');
              } else {
                console.log('Could not restart recognition:', e);
              }
            }
          }
          isRestartingRecognitionRef.current = false;
        }, 100);
      }
    };
    
    // Fired when speech is first detected
    recognition.onspeechstart = () => {
      console.log('Speech detected');
      // Show that user is speaking - this will trigger interrupt if Adam is speaking
      setSpeakingState('user');
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

  // Perform interrupt - stop Adam and prepare for new input
  const performInterrupt = useCallback(() => {
    if (!sessionRef.current) return;
    
    // Prevent double interrupts with cooldown
    const now = Date.now();
    if (isInterruptingRef.current || (now - lastInterruptTimeRef.current) < INTERRUPT_COOLDOWN_MS) {
      console.log('⏳ Interrupt skipped - cooldown active or already interrupting');
      return;
    }
    
    isInterruptingRef.current = true;
    lastInterruptTimeRef.current = now;
    
    console.log('🛑 VAD: Performing interrupt - user is speaking');
    
    // Increment request ID to invalidate any pending responses
    currentRequestIdRef.current++;
    console.log(`New request ID after interrupt: ${currentRequestIdRef.current}`);
    
    // Cancel any pending speak-end timeout
    if (speakEndTimeoutRef.current) {
      clearTimeout(speakEndTimeoutRef.current);
      speakEndTimeoutRef.current = null;
    }
    
    // Cancel any pending transcript processing
    if (processTranscriptTimeoutRef.current) {
      clearTimeout(processTranscriptTimeoutRef.current);
      processTranscriptTimeoutRef.current = null;
    }
    
    // Clear accumulated transcript to start fresh
    accumulatedTranscriptRef.current = '';
    
    // Stop the avatar from speaking
    try {
      sessionRef.current.interrupt();
    } catch (e) {
      console.error('Error interrupting avatar:', e);
    }
    
    // Reset state - allow new transcript to be processed
    isAvatarSpeakingRef.current = false;
    isProcessingRef.current = false;
    pendingResponseRef.current = null;
    lastProcessedTranscriptRef.current = ''; // Clear to allow new question
    lastInterimTranscriptRef.current = ''; // Clear interim transcript
    setIsProcessing(false);
    setSpeakingState('user');
    
    // Reset VAD counters
    consecutiveSpeechFramesRef.current = 0;
    consecutiveSilenceFramesRef.current = 0;
    
    // Restart speech recognition to get a clean slate for the new question
    // This helps avoid partial transcripts from the interrupted speech
    if (recognitionRef.current && isListeningRef.current && !isRestartingRecognitionRef.current) {
      isRestartingRecognitionRef.current = true;
      try {
        recognitionRef.current.stop();
        // Small delay before restarting
        setTimeout(() => {
          if (recognitionRef.current && isListeningRef.current) {
            try {
              recognitionRef.current.start();
              console.log('🔄 Speech recognition restarted after interrupt');
            } catch (e: unknown) {
              if (e instanceof Error && e.name === 'InvalidStateError') {
                console.log('Speech recognition already running after interrupt');
              } else {
                console.log('Could not restart recognition:', e);
              }
            }
          }
          isRestartingRecognitionRef.current = false;
          isInterruptingRef.current = false; // Clear interrupt flag after restart completes
        }, 150);
      } catch (e) {
        console.log('Could not stop recognition for restart:', e);
        isRestartingRecognitionRef.current = false;
        isInterruptingRef.current = false;
      }
    } else {
      // Clear interrupt flag if we didn't restart recognition
      setTimeout(() => {
        isInterruptingRef.current = false;
      }, 200);
    }
  }, []);

  // Start Voice Activity Detection for interrupt
  const startVAD = useCallback(async () => {
    try {
      // Get microphone stream
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: { 
          echoCancellation: true, 
          noiseSuppression: true,
          autoGainControl: true 
        } 
      });
      micStreamRef.current = stream;
      
      // Create audio context and analyser
      const audioContext = new AudioContext();
      audioContextRef.current = audioContext;
      
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 512;
      analyserRef.current = analyser;
      
      const source = audioContext.createMediaStreamSource(stream);
      source.connect(analyser);
      
      // Start VAD interval - check for voice activity every 50ms
      vadIntervalRef.current = setInterval(() => {
        if (!analyserRef.current) return;
        
        const dataArray = new Float32Array(analyserRef.current.fftSize);
        analyserRef.current.getFloatTimeDomainData(dataArray);
        
        // Calculate RMS (Root Mean Square) for volume level
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i] * dataArray[i];
        }
        const rms = Math.sqrt(sum / dataArray.length);
        
        // Check if voice is detected
        const isVoiceDetected = rms > VAD_THRESHOLD;
        
        // Only check for interrupt if Adam is ACTUALLY SPEAKING (audio playing)
        // Don't interrupt during processing/waiting for response - let the user's speech be captured
        if (isAvatarSpeakingRef.current) {
          if (isVoiceDetected) {
            consecutiveSpeechFramesRef.current++;
            consecutiveSilenceFramesRef.current = 0; // Reset silence counter
            console.log(`🎤 VAD: Voice detected (${consecutiveSpeechFramesRef.current}/${VAD_FRAMES_TO_INTERRUPT}) RMS: ${rms.toFixed(4)}`);
            
            if (consecutiveSpeechFramesRef.current >= VAD_FRAMES_TO_INTERRUPT) {
              performInterrupt();
            }
          } else {
            // Reset counter if silence detected
            if (consecutiveSpeechFramesRef.current > 0) {
              consecutiveSpeechFramesRef.current = 0;
            }
          }
        } else {
          // Adam is not speaking - check for silence to process interim transcript
          if (isVoiceDetected) {
            consecutiveSpeechFramesRef.current++;
            consecutiveSilenceFramesRef.current = 0;
          } else {
            consecutiveSpeechFramesRef.current = 0;
            consecutiveSilenceFramesRef.current++;
            
            // If we have an interim transcript and enough silence, process it
            if (consecutiveSilenceFramesRef.current >= VAD_SILENCE_FRAMES_TO_PROCESS) {
              const interimText = lastInterimTranscriptRef.current;
              const wordCount = interimText.trim().split(/\s+/).filter(w => w.length > 0).length;
              
              if (interimText && !isProcessingRef.current) {
                // Only process if we have enough words (avoid processing fragments like "between")
                if (wordCount >= MIN_WORDS_TO_PROCESS) {
                  console.log(`🔇 VAD: Silence detected - processing interim transcript (${wordCount} words): "${interimText}"`);
                  
                  // Clear the interim transcript
                  lastInterimTranscriptRef.current = '';
                  consecutiveSilenceFramesRef.current = 0;
                  
                  // Add to accumulated transcript and process
                  if (interimText !== lastProcessedTranscriptRef.current) {
                    accumulatedTranscriptRef.current = (accumulatedTranscriptRef.current + ' ' + interimText).trim();
                    
                    // Cancel any pending processing timeout
                    if (processTranscriptTimeoutRef.current) {
                      clearTimeout(processTranscriptTimeoutRef.current);
                    }
                    
                    // Process immediately since we detected silence
                    const fullTranscript = accumulatedTranscriptRef.current.trim();
                    if (fullTranscript) {
                      console.log('✅ VAD: Processing transcript after silence:', fullTranscript);
                      setSpeakingState('none');
                      processUserSpeech(fullTranscript);
                      accumulatedTranscriptRef.current = '';
                    }
                  }
                } else {
                  // Too few words - wait longer for more speech
                  // Only log once per silence period
                  if (consecutiveSilenceFramesRef.current === VAD_SILENCE_FRAMES_TO_PROCESS) {
                    console.log(`⏳ VAD: Waiting for more speech (only ${wordCount} words: "${interimText}")`);
                  }
                }
              }
            }
          }
        }
      }, 50); // Check every 50ms
      
      console.log('VAD started for interrupt detection');
    } catch (error) {
      console.error('Failed to start VAD:', error);
    }
  }, [performInterrupt, processUserSpeech]);

  // Stop Voice Activity Detection
  const stopVAD = useCallback(() => {
    if (vadIntervalRef.current) {
      clearInterval(vadIntervalRef.current);
      vadIntervalRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach(track => track.stop());
      micStreamRef.current = null;
    }
    analyserRef.current = null;
    consecutiveSpeechFramesRef.current = 0;
    consecutiveSilenceFramesRef.current = 0;
    lastInterimTranscriptRef.current = '';
    console.log('VAD stopped');
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
          // Start VAD for interrupt detection during avatar speech
          startVAD();
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
        // Ignore if we're in the middle of an interrupt
        if (isInterruptingRef.current) {
          console.log('Avatar started speaking (ignored - interrupt in progress)');
          return;
        }
        
        console.log('Avatar started speaking');
        isAvatarSpeakingRef.current = true;
        setSpeakingState('avatar');
        
        // Cancel any pending "speak ended" handler - avatar is still talking
        if (speakEndTimeoutRef.current) {
          clearTimeout(speakEndTimeoutRef.current);
          speakEndTimeoutRef.current = null;
          console.log('Cancelled speak-end timeout - avatar still speaking');
        }
        
        // IMPORTANT: Make sure speech recognition is running so user can interrupt!
        // But don't try if we're already restarting
        if (recognitionRef.current && isListeningRef.current && !isRestartingRecognitionRef.current) {
          try {
            recognitionRef.current.start();
            console.log('Speech recognition started/restarted - listening for interrupts');
          } catch (e: unknown) {
            // InvalidStateError means recognition is already running - that's fine
            if (e instanceof Error && e.name === 'InvalidStateError') {
              console.log('Speech recognition already running - ready for interrupts');
            } else {
              console.log('Could not start recognition:', e);
            }
          }
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
              } catch (e: unknown) {
                // InvalidStateError means recognition is already running - that's fine
                if (e instanceof Error && e.name === 'InvalidStateError') {
                  console.log('Speech recognition already running - ready for input');
                } else {
                  console.log('Could not start recognition:', e);
                }
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
    
    // Stop VAD
    stopVAD();
    
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
  }, [stopListening, stopVAD, chatSessionId]);

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

  // Manual interrupt - stop Adam and let user speak
  const manualInterrupt = useCallback(() => {
    console.log('🛑 Manual interrupt triggered');
    
    if (!sessionRef.current) return;
    
    // Increment request ID to invalidate any pending responses
    currentRequestIdRef.current++;
    console.log(`New request ID after manual interrupt: ${currentRequestIdRef.current}`);
    
    // Cancel any pending speak-end timeout
    if (speakEndTimeoutRef.current) {
      clearTimeout(speakEndTimeoutRef.current);
      speakEndTimeoutRef.current = null;
    }
    
    // Cancel any pending transcript processing
    if (processTranscriptTimeoutRef.current) {
      clearTimeout(processTranscriptTimeoutRef.current);
      processTranscriptTimeoutRef.current = null;
    }
    
    // Clear accumulated transcript
    accumulatedTranscriptRef.current = '';
    
    // Stop the avatar from speaking
    try {
      sessionRef.current.interrupt();
      toast.success('Adam stopped - speak now!');
    } catch (e) {
      console.error('Error interrupting avatar:', e);
    }
    
    // Reset state
    isAvatarSpeakingRef.current = false;
    isProcessingRef.current = false;
    pendingResponseRef.current = null;
    lastProcessedTranscriptRef.current = '';
    setIsProcessing(false);
    setSpeakingState('none');
    setUserTranscript('');
    
    // Make sure speech recognition is running
    if (recognitionRef.current && isListeningRef.current) {
      try {
        recognitionRef.current.start();
      } catch (e) {
        // Already running, that's fine
      }
    }
  }, []);

  // Toggle audio (speaker)
  const toggleAudio = useCallback(() => {
    if (videoRef.current) {
      videoRef.current.muted = !videoRef.current.muted;
      setIsAudioMuted(videoRef.current.muted);
    }
  }, []);

  // Keyboard shortcut for interrupt (Escape key)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Escape key to interrupt Adam
      if (e.key === 'Escape' && (speakingState === 'avatar' || isProcessing)) {
        e.preventDefault();
        manualInterrupt();
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [speakingState, isProcessing, manualInterrupt]);

  // Cleanup on unmount only
  useEffect(() => {
    return () => {
      // Stop speech recognition
      if (recognitionRef.current && isListeningRef.current) {
        recognitionRef.current.stop();
        isListeningRef.current = false;
      }
      
      // Stop VAD
      if (vadIntervalRef.current) {
        clearInterval(vadIntervalRef.current);
        vadIntervalRef.current = null;
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
        audioContextRef.current = null;
      }
      if (micStreamRef.current) {
        micStreamRef.current.getTracks().forEach(track => track.stop());
        micStreamRef.current = null;
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
      
      {/* Captions - show user transcript or interrupt hint */}
      <div className="h-16 flex items-center justify-center px-4">
        {userTranscript ? (
          <div className="max-w-2xl w-full">
            <p className="text-gray-800 text-lg text-center">
              <span className="text-blue-600 font-medium">You: </span>
              {userTranscript}
            </p>
          </div>
        ) : (speakingState === 'avatar' || isProcessing) ? (
          <div className="max-w-2xl w-full">
            <p className="text-orange-600 text-sm text-center animate-pulse">
              💡 Press <kbd className="px-1 py-0.5 bg-orange-100 rounded text-xs font-mono">Esc</kbd> or click the orange button to interrupt Adam
            </p>
          </div>
        ) : null}
      </div>
      
      {/* Bottom controls */}
      <div className="h-24 bg-white border-t border-gray-200 flex items-center justify-center gap-4 px-4">
        {/* Interrupt button - only shows when Adam is speaking */}
        {(speakingState === 'avatar' || isProcessing) && callState === 'connected' && (
          <button
            onClick={manualInterrupt}
            className="w-14 h-14 rounded-full flex items-center justify-center transition-all shadow-md bg-orange-500 hover:bg-orange-600 text-white animate-pulse"
            title="Stop Adam and speak"
          >
            <StopCircle className="w-6 h-6" />
          </button>
        )}
        
        {/* Mic toggle */}
        <button
          onClick={toggleMic}
          disabled={callState !== 'connected'}
          className={clsx(
            'w-14 h-14 rounded-full flex items-center justify-center transition-all shadow-md',
            isMicMuted
              ? 'bg-red-500 text-white' 
              : 'bg-gray-100 hover:bg-gray-200 text-gray-700',
            callState !== 'connected' && 'cursor-not-allowed'
          )}
          title={isMicMuted ? 'Unmute microphone' : 'Mute microphone'}
        >
          {isMicMuted ? (
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
