import { useRef, useCallback, useState } from 'react';
import { useVAD } from './useVAD';

/**
 * Higher-level hook that integrates VAD with voice response handling.
 * 
 * This hook manages:
 * - Interrupting ongoing responses
 * - Pausing/resuming audio playback
 * - Managing response cancellation
 */
export function useVADIntegration() {
  const abortControllerRef = useRef<AbortController | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [canInterrupt, setCanInterrupt] = useState(false);

  // Initialize VAD
  const {
    isConnected,
    isSpeaking,
    speechDuration,
    startListening,
    stopListening,
    reset,
  } = useVAD({
    sampleRate: 16000,
    aggressiveness: 2,
    onSpeechStart: () => {
      // User started speaking while assistant is responding
      if (isProcessing && canInterrupt) {
        handleInterrupt();
      }
    },
    onSpeechEnd: () => {
      // User stopped speaking
      console.log('User stopped speaking');
    },
  });

  // Handle interrupt
  const handleInterrupt = useCallback(() => {
    console.log('Interrupting response...');
    
    // Abort ongoing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    // Reset state
    setIsProcessing(false);
    setCanInterrupt(false);
    reset();

    // Dispatch custom event for parent component to handle
    window.dispatchEvent(
      new CustomEvent('vad:interrupt', {
        detail: { timestamp: Date.now() },
      })
    );
  }, [reset]);

  // Create abort controller for new request
  const createAbortController = useCallback(() => {
    abortControllerRef.current = new AbortController();
    return abortControllerRef.current;
  }, []);

  // Mark that we're processing a response
  const markProcessing = useCallback((canInterruptResponse: boolean = true) => {
    setIsProcessing(true);
    setCanInterrupt(canInterruptResponse);
  }, []);

  // Mark that processing is done
  const markProcessingDone = useCallback(() => {
    setIsProcessing(false);
    setCanInterrupt(false);
  }, []);

  return {
    // VAD state
    isConnected,
    isSpeaking,
    speechDuration,
    
    // Processing state
    isProcessing,
    canInterrupt,
    
    // VAD controls
    startListening,
    stopListening,
    reset,
    
    // Response handling
    handleInterrupt,
    createAbortController,
    markProcessing,
    markProcessingDone,
  };
}
