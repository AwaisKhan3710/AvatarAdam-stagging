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

  // VAD integration - only enabled when recording
  const {
    isConnected: vadConnected,
    isSpeaking: vadIsSpeaking,
    speechDuration: vadSpeechDuration,
    reset: vadReset,
  } = useVAD({
    enabled: isRecording, // Only connect when recording
    onSpeechStart: () => {
      console.log('🎤 VAD: Speech started');
    },
    onSpeechEnd: () => {
      console.log('🔇 VAD: Speech ended');
    },
  });

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, interimTranscript]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (recordingIntervalRef.current) {
        clearInterval(recordingIntervalRef.current);
      }
      if (currentAudioRef.current) {
        currentAudioRef.current.pause();
      }
    };
  }, []);

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSendMessage();
    }
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Format VAD duration (in ms) to seconds
  const formatVadDuration = (ms: number) => {
    const seconds = Math.floor(ms / 1000);
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Start voice recording with VAD
  const startRecording = useCallback(async () => {
    if (!onSendVoiceMessage) return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000,
        },
      });

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4',
      });

      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        stream.getTracks().forEach(track => track.stop());

        if (audioBlob.size > 0 && onSendVoiceMessage) {
          onSendVoiceMessage(audioBlob);
        }

        audioChunksRef.current = [];
      };

      mediaRecorder.start(100);
      setIsRecording(true);
      setRecordingDuration(0);

      // VAD will auto-start when isRecording becomes true (via enabled prop)

      // Start duration counter
      recordingIntervalRef.current = setInterval(() => {
        setRecordingDuration(prev => prev + 1);
      }, 1000);

      toast.success('Recording started - speak now!');
    } catch (error) {
      console.error('Failed to start recording:', error);
      toast.error('Failed to access microphone');
    }
  }, [onSendVoiceMessage]);

  // Stop voice recording
  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);

      // VAD will auto-stop when isRecording becomes false (via enabled prop)
      vadReset();

      if (recordingIntervalRef.current) {
        clearInterval(recordingIntervalRef.current);
        recordingIntervalRef.current = null;
      }
    }
  }, [isRecording, vadReset]);

  // Play audio message
  const playAudio = useCallback((messageId: string, audioBase64: string) => {
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
      setPlayingMessageId(null);
    }

    const audio = new Audio(`data:audio/mp3;base64,${audioBase64}`);
    currentAudioRef.current = audio;
    setPlayingMessageId(messageId);

    audio.onended = () => {
      currentAudioRef.current = null;
      setPlayingMessageId(null);
    };

    audio.onerror = () => {
      currentAudioRef.current = null;
      setPlayingMessageId(null);
    };

    audio.play().catch(() => {
      setPlayingMessageId(null);
    });
  }, []);

  // Stop audio playback
  const stopAudio = useCallback(() => {
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
      setPlayingMessageId(null);
    }
  }, []);

  // Get the user message that precedes an assistant message
  const getUserInputForMessage = useCallback((messageIndex: number): string => {
    for (let i = messageIndex - 1; i >= 0; i--) {
      if (messages[i].role === 'user') {
        return messages[i].content;
      }
    }
    return '';
  }, [messages]);

  // Build conversation context from messages
  const getConversationContext = useCallback(() => {
    return messages.map(m => ({
      role: m.role,
      content: m.content,
    }));
  }, [messages]);

  // Send to team
  const submitSendToTeam = useCallback(async () => {
    if (!sendToTeamMessageId) return;

    const messageIndex = messages.findIndex(m => m.id === sendToTeamMessageId);
    const message = messages.find(m => m.id === sendToTeamMessageId);
    if (!message || message.role !== 'assistant') return;

    setIsSubmittingSendToTeam(true);
    try {
      const userQuestion = getUserInputForMessage(messageIndex);
      const response = await reportApi.sendToTeam({
        user_question: userQuestion,
        ai_response: message.content,
        conversation_history: getConversationContext(),
        additional_notes: sendToTeamNote || undefined,
        session_id: sessionId,
        dealership_name: dealershipName,
      });

      if (response.success) {
        toast.success('Sent to team successfully!');
        setSendToTeamMessageId(null);
        setSendToTeamNote('');
      } else {
        toast.error(response.message || 'Failed to send to team');
      }
    } catch (error) {
      console.error('Failed to send to team:', error);
      toast.error('Failed to send to team. Please try again.');
    } finally {
      setIsSubmittingSendToTeam(false);
    }
  }, [messages, sendToTeamMessageId, sendToTeamNote, sessionId, dealershipName, getUserInputForMessage, getConversationContext]);

  // Determine recording status text and color - only show when recording
  const getRecordingStatus = () => {
    if (!isRecording) return null;
    
    if (vadIsSpeaking) {
      return {
        text: `🎤 Speaking ${formatVadDuration(vadSpeechDuration)}`,
        bgColor: 'bg-green-50',
        textColor: 'text-green-600',
        borderColor: 'border-green-200',
        icon: <Radio className="w-4 h-4 animate-pulse text-green-500" />,
        dotColor: 'bg-green-500',
      };
    } else {
      return {
        text: '🔇 Silent - Waiting for speech...',
        bgColor: 'bg-yellow-50',
        textColor: 'text-yellow-600',
        borderColor: 'border-yellow-200',
        icon: <VolumeX className="w-4 h-4 text-yellow-500" />,
        dotColor: 'bg-yellow-500',
      };
    }
  };

  const recordingStatus = getRecordingStatus();

  return (
    <div className="flex flex-col h-full bg-gradient-to-b from-slate-50 to-white">
      {/* Header */}
      <div className="h-14 bg-white border-b border-gray-100 flex items-center justify-between px-4 shrink-0 shadow-sm">
        <div className="flex items-center gap-3">
          <div className={clsx(
            'w-10 h-10 rounded-full flex items-center justify-center',
            mode === 'training' ? 'bg-gradient-to-br from-blue-500 to-indigo-600' : 'bg-gradient-to-br from-emerald-500 to-teal-600'
          )}>
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-800">
              {mode === 'training' ? 'Adam - AI Trainer' : 'Practice Customer'}
            </h3>
            <p className="text-xs text-gray-500">
              {voiceState === 'speaking' ? '🔊 Speaking...' :
               voiceState === 'processing' ? '🤔 Thinking...' :
               voiceState === 'listening' || voiceState === 'recording' ? '🎤 Listening...' :
               'Online'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* VAD Connection Status - only show when recording */}
          {isRecording && (
            <span className={clsx(
              'text-xs px-2 py-1 rounded-full',
              vadConnected ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
            )}>
              {vadConnected ? '✓ VAD Active' : '⏳ Connecting...'}
            </span>
          )}
          <span className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded-full">
            {messages.length} messages
          </span>
        </div>
      </div>

      {/* Messages Container */}
      <div
        ref={messagesContainerRef}
        className="flex-1 overflow-y-auto px-4 py-4 space-y-3"
        style={{
          backgroundImage: 'radial-gradient(circle at 1px 1px, #e5e7eb 1px, transparent 0)',
          backgroundSize: '24px 24px'
        }}
      >
        {messages.length === 0 && !interimTranscript && (
          <div className="flex flex-col items-center justify-center h-full">
            <div className={clsx(
              'w-20 h-20 rounded-full flex items-center justify-center mb-4',
              mode === 'training' ? 'bg-gradient-to-br from-blue-100 to-indigo-100' : 'bg-gradient-to-br from-emerald-100 to-teal-100'
            )}>
              <Bot className={clsx(
                'w-10 h-10',
                mode === 'training' ? 'text-indigo-500' : 'text-teal-500'
              )} />
            </div>
            <p className="text-sm text-gray-600 text-center font-medium">
              {mode === 'training'
                ? 'Start a conversation with Adam'
                : 'Practice with a simulated customer'}
            </p>
            <p className="text-xs text-gray-400 mt-1 text-center">
              Send a message or record your voice
            </p>
          </div>
        )}

        {messages.map((message, index) => {
          const isUser = message.role === 'user';
          const showAvatar = index === 0 || messages[index - 1]?.role !== message.role;

          return (
            <div
              key={message.id}
              className={clsx(
                'flex gap-2',
                isUser ? 'flex-row-reverse' : 'flex-row'
              )}
            >
              {/* Avatar */}
              {showAvatar ? (
                <div
                  className={clsx(
                    'w-8 h-8 rounded-full flex items-center justify-center shrink-0 shadow-sm',
                    isUser
                      ? 'bg-gradient-to-br from-blue-500 to-blue-600'
                      : mode === 'training'
                        ? 'bg-gradient-to-br from-indigo-500 to-purple-600'
                        : 'bg-gradient-to-br from-emerald-500 to-teal-600'
                  )}
                >
                  {isUser ? (
                    <User className="w-4 h-4 text-white" />
                  ) : (
                    <Bot className="w-4 h-4 text-white" />
                  )}
                </div>
              ) : (
                <div className="w-8 shrink-0" />
              )}

              {/* Message Bubble */}
              <div className={clsx(
                'max-w-[80%] group relative',
                isUser ? 'items-end' : 'items-start'
              )}>
                <div
                  className={clsx(
                    'rounded-2xl px-4 py-2.5 shadow-sm relative',
                    isUser
                      ? 'bg-gradient-to-br from-blue-500 to-blue-600 text-white rounded-tr-md'
                      : 'bg-white text-gray-800 rounded-tl-md border border-gray-100'
                  )}
                >
                  {/* Audio Play Button for Assistant Messages */}
                  {!isUser && message.audioBase64 && (
                    <button
                      onClick={() => playingMessageId === message.id ? stopAudio() : playAudio(message.id, message.audioBase64!)}
                      className={clsx(
                        'absolute -top-2 -right-2 w-7 h-7 rounded-full flex items-center justify-center shadow-md transition-all',
                        playingMessageId === message.id
                          ? 'bg-red-500 hover:bg-red-600'
                          : 'bg-indigo-500 hover:bg-indigo-600'
                      )}
                    >
                      {playingMessageId === message.id ? (
                        <Square className="w-3 h-3 text-white" />
                      ) : (
                        <Volume2 className="w-3.5 h-3.5 text-white" />
                      )}
                    </button>
                  )}

                  {/* Voice Message Indicator */}
                  {message.isVoiceMessage && (
                    <div className={clsx(
                      'flex items-center gap-1.5 mb-1 text-xs',
                      isUser ? 'text-blue-100' : 'text-gray-400'
                    )}>
                      <Mic className="w-3 h-3" />
                      <span>Voice message</span>
                    </div>
                  )}

                  {/* Message Content */}
                  <p className="text-sm whitespace-pre-wrap break-words leading-relaxed">
                    {message.content}
                    {message.isStreaming && (
                      <span className="inline-block ml-1 animate-pulse">▊</span>
                    )}
                  </p>

                  {/* Timestamp */}
                  <p
                    className={clsx(
                      'text-[10px] mt-1.5 text-right',
                      isUser ? 'text-blue-200' : 'text-gray-400'
                    )}
                  >
                    {formatTime(message.timestamp)}
                  </p>
                </div>

                {/* Send to Team Button */}
                {!isUser && !message.isStreaming && (
                  <div className="flex justify-end mt-1">
                    <button
                      onClick={() => setSendToTeamMessageId(message.id)}
                      className="flex items-center gap-1.5 text-xs text-emerald-600 hover:text-emerald-700 transition-colors"
                    >
                      <SendHorizontal className="w-3.5 h-3.5" />
                      <span>Send to Team</span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {/* Send to Team Modal */}
        {sendToTeamMessageId && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
              <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-emerald-50 to-teal-50">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center">
                    <SendHorizontal className="w-5 h-5 text-emerald-600" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">Send to Team</h3>
                    <p className="text-sm text-gray-500">Share this conversation with your team</p>
                  </div>
                </div>
                <button
                  onClick={() => {
                    setSendToTeamMessageId(null);
                    setSendToTeamNote('');
                  }}
                  className="p-2 hover:bg-gray-100 rounded-full transition-colors"
                >
                  <X className="w-5 h-5 text-gray-500" />
                </button>
              </div>

              <div className="p-6 overflow-y-auto max-h-[60vh] space-y-4">
                {(() => {
                  const targetMessage = messages.find(m => m.id === sendToTeamMessageId);
                  const targetIndex = messages.findIndex(m => m.id === sendToTeamMessageId);
                  const userMessage = targetIndex > 0 ? messages[targetIndex - 1] : null;

                  return (
                    <>
                      {userMessage && userMessage.role === 'user' && (
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">Your Question</label>
                          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                            <p className="text-sm text-gray-800">{userMessage.content}</p>
                          </div>
                        </div>
                      )}
                      {targetMessage && (
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">AI Response</label>
                          <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3">
                            <p className="text-sm text-gray-800">{targetMessage.content}</p>
                          </div>
                        </div>
                      )}
                    </>
                  );
                })()}

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Full Conversation History</label>
                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 max-h-40 overflow-y-auto">
                    <div className="space-y-2">
                      {messages.map((msg, idx) => (
                        <div key={idx} className="text-sm">
                          <span className={clsx('font-medium', msg.role === 'user' ? 'text-blue-600' : 'text-emerald-600')}>
                            {msg.role === 'user' ? 'You: ' : 'AI: '}
                          </span>
                          <span className="text-gray-700">{msg.content}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Additional Notes (Optional)</label>
                  <textarea
                    value={sendToTeamNote}
                    onChange={(e) => setSendToTeamNote(e.target.value)}
                    placeholder="Add any context or notes for your team..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 resize-none"
                    rows={3}
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200 bg-gray-50">
                <button
                  onClick={() => {
                    setSendToTeamMessageId(null);
                    setSendToTeamNote('');
                  }}
                  className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={submitSendToTeam}
                  disabled={isSubmittingSendToTeam}
                  className="px-4 py-2 text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {isSubmittingSendToTeam ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Sending...
                    </>
                  ) : (
                    <>
                      <SendHorizontal className="w-4 h-4" />
                      Send to Team
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Show interim transcript as a pending user message */}
        {interimTranscript && (
          <div className="flex gap-2 flex-row-reverse">
            <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 bg-gradient-to-br from-blue-500 to-blue-600 shadow-sm">
              <User className="w-4 h-4 text-white" />
            </div>
            <div className="max-w-[80%]">
              <div className="rounded-2xl px-4 py-2.5 bg-blue-100 text-blue-700 rounded-tr-md border-2 border-dashed border-blue-300">
                <div className="flex items-center gap-1.5 mb-1 text-xs text-blue-500">
                  <Mic className="w-3 h-3 animate-pulse" />
                  <span>Listening...</span>
                </div>
                <p className="text-sm italic">{interimTranscript}...</p>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-100 p-3 bg-white shrink-0 shadow-lg">
        {/* Enhanced Recording Indicator with VAD Status */}
        {isRecording && recordingStatus && (
          <div className={clsx(
            'flex items-center justify-between mb-2 py-2 px-3 rounded-lg border',
            recordingStatus.bgColor,
            recordingStatus.borderColor
          )}>
            <div className="flex items-center gap-2">
              <div className={clsx('w-3 h-3 rounded-full animate-pulse', recordingStatus.dotColor)} />
              {recordingStatus.icon}
              <span className={clsx('text-sm font-medium', recordingStatus.textColor)}>
                {recordingStatus.text}
              </span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs text-gray-500 bg-white px-2 py-1 rounded">
                Total: {formatDuration(recordingDuration)}
              </span>
              {/* Stop/Interrupt Button */}
              <button
                onClick={stopRecording}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-red-500 hover:bg-red-600 text-white text-xs font-medium rounded-full transition-colors shadow-sm"
              >
                <Square className="w-3 h-3" />
                {vadIsSpeaking ? 'Interrupt' : 'Stop'}
              </button>
            </div>
          </div>
        )}

        <div className="flex items-center gap-2">
          {/* Text Input */}
          <div className="flex-1 relative">
            <input
              type="text"
              value={textInput}
              onChange={(e) => onTextInputChange(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={isRecording ? (vadIsSpeaking ? 'Speaking...' : 'Waiting for speech...') : 'Type a message...'}
              disabled={isDisabled || isRecording}
              className="w-full px-4 py-2.5 bg-gray-100 border-0 rounded-full text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white disabled:bg-gray-50 disabled:text-gray-400 disabled:cursor-not-allowed transition-all"
            />
          </div>

          {/* Send Button or Voice Record Button */}
          {textInput.trim() ? (
            <button
              onClick={onSendMessage}
              disabled={isDisabled || isRecording}
              className={clsx(
                'w-10 h-10 rounded-full flex items-center justify-center transition-all shrink-0',
                !isDisabled && !isRecording
                  ? 'bg-gradient-to-br from-blue-500 to-blue-600 text-white hover:from-blue-600 hover:to-blue-700 shadow-md'
                  : 'bg-gray-100 text-gray-400 cursor-not-allowed'
              )}
            >
              {isDisabled && !isRecording ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </button>
          ) : onSendVoiceMessage ? (
            <button
              onClick={isRecording ? stopRecording : startRecording}
              disabled={isDisabled && !isRecording}
              className={clsx(
                'w-10 h-10 rounded-full flex items-center justify-center transition-all shrink-0 shadow-md',
                isRecording
                  ? vadIsSpeaking
                    ? 'bg-green-500 hover:bg-green-600 text-white animate-pulse'
                    : 'bg-yellow-500 hover:bg-yellow-600 text-white'
                  : 'bg-gray-100 hover:bg-gray-200 text-gray-600 disabled:opacity-50 disabled:cursor-not-allowed'
              )}
              title={isRecording ? (vadIsSpeaking ? 'Speaking - Click to stop' : 'Silent - Click to stop') : 'Click to record'}
            >
              {isRecording ? (
                vadIsSpeaking ? (
                  <Radio className="w-5 h-5" />
                ) : (
                  <MicOff className="w-5 h-5" />
                )
              ) : (
                <Mic className="w-5 h-5" />
              )}
            </button>
          ) : (
            <button
              onClick={onSendMessage}
              disabled={true}
              className="w-10 h-10 rounded-full flex items-center justify-center transition-all shrink-0 bg-gray-100 text-gray-400 cursor-not-allowed"
            >
              <Send className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
