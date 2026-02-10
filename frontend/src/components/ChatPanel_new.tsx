import { useRef, useEffect, useState, useCallback } from 'react';
import { Send, User, Bot, Loader2, Mic, MicOff, Square, Volume2, X, SendHorizontal, Radio, VolumeX } from 'lucide-react';
import clsx from 'clsx';
import toast from 'react-hot-toast';
import type { UIChatMessage } from '../types';
import { reportApi } from '../services/api';
import { useVAD } from '../hooks/useVAD';

interface ChatPanelProps {
  messages: UIChatMessage[];
  textInput: string;
  onTextInputChange: (value: string) => void;
  onSendMessage: () => void;
  onSendVoiceMessage?: (audioBlob: Blob) => void;
  isDisabled: boolean;
  mode: 'training' | 'roleplay';
  interimTranscript?: string;
  voiceState?: 'idle' | 'connecting' | 'listening' | 'recording' | 'processing' | 'speaking';
  sessionId?: string;
  dealershipName?: string;
}

export default function ChatPanel({
  messages,
  textInput,
  onTextInputChange,
  onSendMessage,
  onSendVoiceMessage,
  isDisabled,
  mode,
  interimTranscript,
  voiceState = 'idle',
  sessionId,
  dealershipName,
}: ChatPanelProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const [isRecording, setIsRecording] = useState(false);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [playingMessageId, setPlayingMessageId] = useState<string | null>(null);
  const [sendToTeamMessageId, setSendToTeamMessageId] = useState<string | null>(null);
  const [sendToTeamNote, setSendToTeamNote] = useState('');
  const [isSubmittingSendToTeam, setIsSubmittingSendToTeam] = useState(false);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);
  const recordingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // VAD integration for speech detection
  const [vadEnabled, setVadEnabled] = useState(false);
  const {
    isConnected: vadConnected,
    isSpeaking: vadIsSpeaking,
    speechDuration: vadSpeechDuration,
    startListening: vadStartListening,
    stopListening: vadStopListening,
    reset: vadReset,
  } = useVAD({
    enabled: vadEnabled && isRecording,
    onSpeechStart: () => {
      console.log('VAD: Speech started');
    },
    onSpeechEnd: () => {
      console.log('VAD: Speech ended');
    },
  });
