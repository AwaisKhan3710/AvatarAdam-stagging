import { useState } from 'react';
import { Mic, Square } from 'lucide-react';
import clsx from 'clsx';

interface InterruptButtonProps {
  isSpeaking: boolean;
  isListening: boolean;
  speechDuration: number;
  onInterrupt: () => void;
  onStartListening: () => void;
  onStopListening: () => void;
  disabled?: boolean;
}

/**
 * Google Meet-style interrupt button.
 * 
 * Features:
 * - Shows when assistant is speaking
 * - Allows user to interrupt with a click
 * - Visual feedback with animation
 * - Speech duration display
 */
export default function InterruptButton({
  isSpeaking,
  isListening,
  speechDuration,
  onInterrupt,
  onStartListening,
  onStopListening,
  disabled = false,
}: InterruptButtonProps) {
  const [isHovered, setIsHovered] = useState(false);

  // Format duration as MM:SS
  const formatDuration = (ms: number) => {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  const handleClick = () => {
    if (isSpeaking) {
      onInterrupt();
    } else if (isListening) {
      onStopListening();
    } else {
      onStartListening();
    }
  };

  // Determine button state and styling
  const isActive = isSpeaking || isListening;
  const buttonColor = isSpeaking ? 'bg-red-500 hover:bg-red-600' : 'bg-blue-500 hover:bg-blue-600';
  const pulseColor = isSpeaking ? 'bg-red-400' : 'bg-blue-400';

  return (
    <div className="flex flex-col items-center gap-2">
      {/* Main button */}
      <button
        onClick={handleClick}
        disabled={disabled}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        className={clsx(
          'relative w-16 h-16 rounded-full flex items-center justify-center',
          'transition-all duration-200 transform',
          'shadow-lg hover:shadow-xl',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          buttonColor,
          isActive && 'scale-110',
          isHovered && !disabled && 'scale-105'
        )}
      >
        {/* Pulse animation when speaking */}
        {isSpeaking && (
          <>
            <div
              className={clsx(
                'absolute inset-0 rounded-full',
                pulseColor,
                'animate-pulse opacity-75'
              )}
            />
            <div
              className={clsx(
                'absolute inset-0 rounded-full border-2',
                'border-red-300 animate-ping'
              )}
            />
          </>
        )}

        {/* Icon */}
        <div className="relative z-10 text-white">
          {isSpeaking ? (
            <Square className="w-6 h-6 fill-current" />
          ) : (
            <Mic className="w-6 h-6" />
          )}
        </div>
      </button>

      {/* Status text */}
      <div className="text-center text-sm">
        {isSpeaking && (
          <div className="flex flex-col items-center gap-1">
            <span className="text-red-600 font-semibold">Click to interrupt</span>
            <span className="text-gray-500 text-xs">{formatDuration(speechDuration)}</span>
          </div>
        )}
        {isListening && !isSpeaking && (
          <span className="text-blue-600 font-semibold">Listening...</span>
        )}
        {!isActive && (
          <span className="text-gray-500">Click to speak</span>
        )}
      </div>

      {/* Tooltip on hover */}
      {isHovered && !disabled && (
        <div className="absolute bottom-full mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg whitespace-nowrap">
          {isSpeaking
            ? 'Click to interrupt the assistant'
            : isListening
            ? 'Click to stop listening'
            : 'Click to start speaking'}
          <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-gray-900" />
        </div>
      )}
    </div>
  );
}
