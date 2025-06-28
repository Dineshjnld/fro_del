import React, { useState, useEffect } from 'react';
import { useVoiceRecording } from '../hooks/useVoiceRecording';
import { MicrophoneIcon } from './icons/MicrophoneIcon';
import { SpinnerIcon } from './icons/SpinnerIcon';

interface VoiceInputProps {
  onTranscription: (text: string) => void;
  disabled?: boolean;
}

export const VoiceInput: React.FC<VoiceInputProps> = ({ onTranscription, disabled = false }) => {
  const { state, startRecording, stopRecording, setLanguage, clearError } = useVoiceRecording();
  const [supportedLanguages, setSupportedLanguages] = useState([
    { code: 'te', name: 'Telugu', native_name: 'తెలుగు' },
    { code: 'hi', name: 'Hindi', native_name: 'हिन्दी' },
    { code: 'en', name: 'English', native_name: 'English' }
  ]);

  useEffect(() => {
    // Fetch supported languages from backend
    fetch('http://127.0.0.1:8000/api/voice/languages')
      .then(res => res.json())
      .then(data => {
        if (data.languages) {
          setSupportedLanguages(data.languages);
        }
      })
      .catch(err => console.warn('Could not fetch voice languages:', err));
  }, []);

  const handleVoiceToggle = async () => {
    if (disabled) return;

    try {
      if (state.isRecording) {
        const result = await stopRecording();
        if (result && result.text) {
          onTranscription(result.text);
        }
      } else {
        await startRecording();
      }
    } catch (error) {
      console.error('Voice recording error:', error);
    }
  };

  const getButtonState = () => {
    if (state.isProcessing) return 'processing';
    if (state.isRecording) return 'recording';
    return 'idle';
  };

  const getButtonIcon = () => {
    if (state.isProcessing) return <SpinnerIcon className="w-5 h-5" />;
    return <MicrophoneIcon />;
  };

  const getButtonColor = () => {
    if (state.isProcessing) return 'bg-yellow-500 hover:bg-yellow-600';
    if (state.isRecording) return 'bg-red-500 hover:bg-red-600 animate-pulse';
    return 'bg-blue-600 hover:bg-blue-700';
  };

  const getButtonTitle = () => {
    if (state.isProcessing) return 'Processing audio...';
    if (state.isRecording) return 'Click to stop recording';
    return 'Click to start voice input';
  };

  return (
    <div className="flex flex-col items-center space-y-3">
      {/* Language Selector */}
      <div className="flex items-center space-x-2">
        <label htmlFor="voice-language" className="text-sm font-medium text-gray-700">
          Voice Language:
        </label>
        <select
          id="voice-language"
          value={state.language}
          onChange={(e) => setLanguage(e.target.value)}
          disabled={state.isRecording || state.isProcessing || disabled}
          className="text-sm border border-gray-300 rounded-md px-2 py-1 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50"
        >
          {supportedLanguages.map((lang) => (
            <option key={lang.code} value={lang.code}>
              {lang.native_name} ({lang.name})
            </option>
          ))}
        </select>
      </div>

      {/* Voice Button */}
      <button
        onClick={handleVoiceToggle}
        disabled={disabled}
        title={getButtonTitle()}
        className={`
          flex items-center justify-center w-12 h-12 rounded-full text-white transition-all duration-200
          ${getButtonColor()}
          ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
          ${state.isRecording ? 'scale-110' : 'hover:scale-105'}
        `}
      >
        {getButtonIcon()}
      </button>

      {/* Status Messages */}
      {state.isRecording && (
        <div className="text-sm text-red-600 font-medium animate-pulse">
          🎤 Recording... Click to stop
        </div>
      )}

      {state.isProcessing && (
        <div className="text-sm text-yellow-600 font-medium">
          🔄 Processing audio with {state.language === 'te' ? 'IndicConformer' : 'Whisper'}...
        </div>
      )}

      {state.error && (
        <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md px-3 py-2 max-w-xs text-center">
          ❌ {state.error}
          <button
            onClick={clearError}
            className="ml-2 text-red-800 hover:text-red-900 underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Model Info */}
      <div className="text-xs text-gray-500 text-center max-w-xs">
        Using {state.language === 'te' || state.language === 'hi' ? 'IndicConformer' : 'Whisper'} model
        {state.language === 'te' && ' (optimized for Telugu)'}
        {state.language === 'hi' && ' (optimized for Hindi)'}
      </div>
    </div>
  );
};