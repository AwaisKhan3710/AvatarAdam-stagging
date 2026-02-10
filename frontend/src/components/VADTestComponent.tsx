import { useState } from 'react';
import { useVAD } from '../hooks/useVAD';
import InterruptButton from './InterruptButton';

/**
 * VAD Test Component
 * 
 * Use this component to test VAD functionality in development
 * 
 * Features:
 * - Test WebSocket connection
 * - Test speech detection
 * - Test interrupt button
 * - Monitor VAD events
 * - Check performance metrics
 */
export default function VADTestComponent() {
  const [logs, setLogs] = useState<string[]>([]);
  const [testRunning, setTestRunning] = useState(false);

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
      addLog('✓ Speech detected - STARTED');
    },
    onSpeechEnd: () => {
      addLog('✓ Speech detected - ENDED');
    },
    onVADEvent: (event) => {
      if (event.speech_started) {
        addLog(`📊 Speech started (duration: ${event.duration_ms}ms)`);
      }
      if (event.speech_ended) {
        addLog(`📊 Speech ended (total duration: ${event.duration_ms}ms)`);
      }
    },
  });

  const addLog = (message: string) => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs((prev) => [...prev, `[${timestamp}] ${message}`]);
  };

  const clearLogs = () => {
    setLogs([]);
  };

  const handleStartListening = async () => {
    try {
      addLog('🎤 Starting microphone...');
      await startListening();
      addLog('✓ Microphone started');
      setTestRunning(true);
    } catch (error) {
      addLog(`✗ Error starting microphone: ${error}`);
    }
  };

  const handleStopListening = () => {
    try {
      addLog('🎤 Stopping microphone...');
      stopListening();
      addLog('✓ Microphone stopped');
      setTestRunning(false);
    } catch (error) {
      addLog(`✗ Error stopping microphone: ${error}`);
    }
  };

  const handleInterrupt = () => {
    addLog('🛑 Interrupt triggered');
    reset();
  };

  const runConnectionTest = () => {
    addLog('🔌 Testing WebSocket connection...');
    if (isConnected) {
      addLog('✓ WebSocket connected');
    } else {
      addLog('⏳ Waiting for connection...');
      setTimeout(() => {
        if (isConnected) {
          addLog('✓ WebSocket connected');
        } else {
          addLog('✗ WebSocket connection failed');
        }
      }, 3000);
    }
  };

  const runMicrophoneTest = async () => {
    addLog('🎤 Testing microphone access...');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      addLog('✓ Microphone access granted');
      stream.getTracks().forEach((track) => track.stop());
    } catch (error) {
      addLog(`✗ Microphone access denied: ${error}`);
    }
  };

  const runSpeechDetectionTest = () => {
    addLog('🗣️ Speech detection test started');
    addLog('📝 Instructions: Speak into your microphone for 5 seconds');
    
    handleStartListening();
    
    setTimeout(() => {
      handleStopListening();
      addLog('✓ Speech detection test completed');
    }, 5000);
  };

  return (
    <div className="w-full max-w-4xl mx-auto p-6 bg-white rounded-lg shadow-lg">
      <h1 className="text-3xl font-bold mb-6 text-gray-800">
        🧪 VAD Test Component
      </h1>

      {/* Status Section */}
      <div className="mb-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
        <h2 className="text-xl font-semibold mb-4 text-gray-700">Status</h2>
        
        <div className="grid grid-cols-2 gap-4">
          <div className="p-3 bg-white rounded border border-gray-200">
            <p className="text-sm text-gray-600">WebSocket Connection</p>
            <p className={`text-lg font-bold ${isConnected ? 'text-green-600' : 'text-red-600'}`}>
              {isConnected ? '✓ Connected' : '✗ Disconnected'}
            </p>
          </div>

          <div className="p-3 bg-white rounded border border-gray-200">
            <p className="text-sm text-gray-600">Speech Detection</p>
            <p className={`text-lg font-bold ${isSpeaking ? 'text-green-600' : 'text-gray-600'}`}>
              {isSpeaking ? '✓ Speaking' : '○ Silent'}
            </p>
          </div>

          <div className="p-3 bg-white rounded border border-gray-200">
            <p className="text-sm text-gray-600">Speech Duration</p>
            <p className="text-lg font-bold text-blue-600">
              {Math.floor(speechDuration / 1000)}s {speechDuration % 1000}ms
            </p>
          </div>

          <div className="p-3 bg-white rounded border border-gray-200">
            <p className="text-sm text-gray-600">Test Status</p>
            <p className={`text-lg font-bold ${testRunning ? 'text-orange-600' : 'text-gray-600'}`}>
              {testRunning ? '⏳ Running' : '○ Idle'}
            </p>
          </div>
        </div>
      </div>

      {/* Controls Section */}
      <div className="mb-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
        <h2 className="text-xl font-semibold mb-4 text-gray-700">Controls</h2>
        
        <div className="flex flex-wrap gap-2">
          <button
            onClick={runConnectionTest}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition"
          >
            🔌 Test Connection
          </button>

          <button
            onClick={runMicrophoneTest}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition"
          >
            🎤 Test Microphone
          </button>

          <button
            onClick={runSpeechDetectionTest}
            disabled={testRunning}
            className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 transition disabled:opacity-50"
          >
            🗣️ Test Speech Detection
          </button>

          <button
            onClick={handleStartListening}
            disabled={testRunning}
            className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 transition disabled:opacity-50"
          >
            ▶️ Start Listening
          </button>

          <button
            onClick={handleStopListening}
            disabled={!testRunning}
            className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 transition disabled:opacity-50"
          >
            ⏹️ Stop Listening
          </button>

          <button
            onClick={clearLogs}
            className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 transition"
          >
            🗑️ Clear Logs
          </button>
        </div>
      </div>

      {/* Interrupt Button Test */}
      <div className="mb-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
        <h2 className="text-xl font-semibold mb-4 text-gray-700">Interrupt Button Test</h2>
        
        <div className="flex justify-center">
          <InterruptButton
            isSpeaking={isSpeaking}
            isListening={testRunning}
            speechDuration={speechDuration}
            onInterrupt={handleInterrupt}
            onStartListening={handleStartListening}
            onStopListening={handleStopListening}
          />
        </div>
      </div>

      {/* Logs Section */}
      <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
        <h2 className="text-xl font-semibold mb-4 text-gray-700">Event Logs</h2>
        
        <div className="bg-black text-green-400 p-4 rounded font-mono text-sm h-64 overflow-y-auto">
          {logs.length === 0 ? (
            <p className="text-gray-500">No events yet. Run a test to see logs.</p>
          ) : (
            logs.map((log, index) => (
              <div key={index} className="mb-1">
                {log}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Instructions */}
      <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
        <h3 className="font-semibold text-blue-900 mb-2">📖 Instructions</h3>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>1. Click "Test Connection" to verify WebSocket connection</li>
          <li>2. Click "Test Microphone" to check microphone access</li>
          <li>3. Click "Test Speech Detection" to test VAD functionality</li>
          <li>4. Speak into your microphone when prompted</li>
          <li>5. Check the logs for event details</li>
          <li>6. Use the Interrupt Button to test interrupt functionality</li>
        </ul>
      </div>

      {/* Test Results */}
      <div className="mt-6 p-4 bg-green-50 rounded-lg border border-green-200">
        <h3 className="font-semibold text-green-900 mb-2">✓ Test Checklist</h3>
        <ul className="text-sm text-green-800 space-y-1">
          <li>
            {isConnected ? '✓' : '○'} WebSocket connection established
          </li>
          <li>
            {logs.some((l) => l.includes('Speech detected')) ? '✓' : '○'} Speech detection working
          </li>
          <li>
            {logs.some((l) => l.includes('Interrupt')) ? '✓' : '○'} Interrupt functionality working
          </li>
          <li>
            {logs.length > 0 ? '✓' : '○'} Event logging working
          </li>
        </ul>
      </div>
    </div>
  );
}
