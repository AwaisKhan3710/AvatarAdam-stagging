/**
 * Chat - Text chat interface with AI trainer
 */

import { useVoiceChat } from '../hooks/useVoiceChat';
import { Wifi, WifiOff, Building2, RotateCcw } from 'lucide-react';
import clsx from 'clsx';
import ChatPanel from '../components/ChatPanel';

export default function Chat() {
  const {
    user,
    mode,
    setMode,
    voiceState,
    textInput,
    setTextInput,
    isConnected,
    interimTranscript,
    chatMessages,
    dealerships,
    selectedDealershipId,
    setSelectedDealershipId,
    isLoadingDealerships,
    isSuperAdmin,
    dealershipId,
    sendTextMessage,
    handleVoiceMessage,
    resetConversation,
  } = useVoiceChat();

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
            <span>{isConnected ? 'Connected' : 'Connecting...'}</span>
          </div>

          {/* Dealership Selector */}
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

      {/* Chat Panel */}
      <main className="flex-1 flex overflow-hidden">
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
            dealershipName={dealerships.find(d => d.id === dealershipId)?.name}
          />
        </div>
      </main>
    </div>
  );
}
