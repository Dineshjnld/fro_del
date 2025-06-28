import React, { useState, useEffect } from 'react';
import { useVoiceRecording } from '../hooks/useVoiceRecording'; // Adjusted path
import { MicrophoneIcon } from './icons/MicrophoneIcon';     // Assuming icons are in ./components/icons/
import { SpinnerIcon } from './icons/SpinnerIcon';         // Assuming icons are in ./components/icons/
import { getSupportedLanguagesFromBackend } from '../services/voiceService'; // Use the new service
import type { Language } from '../types'; // Assuming a Language type

interface VoiceInputProps {
  onTranscription: (text: string) => void;
  disabled?: boolean;
}

export const VoiceInput: React.FC<VoiceInputProps> = ({ onTranscription, disabled = false }) => {
  const { state, startRecording, stopRecording, setLanguage, clearError } = useVoiceRecording();
  const [supportedLanguages, setSupportedLanguages] = useState<Language[]>([
    { code: 'te', name: 'Telugu', native_name: 'తెలుగు' }, // Default fallback
    { code: 'hi', name: 'Hindi', native_name: 'हिन्दी' },
    { code: 'en', name: 'English', native_name: 'English' }
  ]);
  const [initialLanguageFetched, setInitialLanguageFetched] = useState(false);

  useEffect(() => {
    const fetchLangs = async () => {
      try {
        const langs = await getSupportedLanguagesFromBackend();
        if (langs && langs.length > 0) {
          setSupportedLanguages(langs);
          // Set initial language in useVoiceRecording hook if not already set by user
          // And if current state.language isn't in the new list, default to the first one.
          const currentLangExists = langs.some(l => l.code === state.language);
          if (!currentLangExists) {
            setLanguage(langs[0].code);
          }
        }
      } catch (err) {
        console.warn('Could not fetch voice languages from backend:', err);
        // Keep default languages if fetch fails
      } finally {
        setInitialLanguageFetched(true);
      }
    };
    fetchLangs();
  }, [setLanguage]); // Removed state.language from dependency to avoid loop, setLanguage is stable

  const handleVoiceToggle = async () => {
    if (disabled || !initialLanguageFetched) return; // Don't allow toggle if languages not fetched yet

    clearError(); // Clear previous errors on new attempt
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
      // Error is now set in useVoiceRecording hook's state.
      // No need to console.error here as the hook handles it.
      // The UI will display state.error.
    }
  };

  const getButtonState = () => {
    if (state.isProcessing) return 'processing';
    if (state.isRecording) return 'recording';
    return 'idle';
  };

  const getButtonIcon = () => {
    if (state.isProcessing) return <SpinnerIcon className="w-5 h-5 animate-spin" />;
    return <MicrophoneIcon className="w-5 h-5" />;
  };

  const getButtonColor = () => {
    if (state.isProcessing) return 'bg-yellow-500 hover:bg-yellow-600';
    if (state.isRecording) return 'bg-red-500 hover:bg-red-600 animate-pulse';
    if (disabled || !initialLanguageFetched) return 'bg-gray-400';
    return 'bg-blue-600 hover:bg-blue-700';
  };

  const getButtonTitle = () => {
    if (disabled) return 'Voice input disabled';
    if (!initialLanguageFetched) return 'Loading languages...';
    if (state.isProcessing) return 'Processing audio...';
    if (state.isRecording) return 'Click to stop recording';
    return 'Click to start voice input';
  };

  return (
    <div className="flex flex-col items-center space-y-3 my-4">
      <div className="flex items-center space-x-2">
        <label htmlFor="voice-language" className="text-sm font-medium text-gray-700">
          Language:
        </label>
        <select
          id="voice-language"
          value={state.language}
          onChange={(e) => setLanguage(e.target.value)}
          disabled={state.isRecording || state.isProcessing || disabled || !initialLanguageFetched}
          className="text-sm border border-gray-300 rounded-md px-2 py-1 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 bg-white"
        >
          {initialLanguageFetched ? (
            supportedLanguages.map((lang) => (
              <option key={lang.code} value={lang.code}>
                {lang.native_name} ({lang.name})
              </option>
            ))
          ) : (
            <option value={state.language} disabled>Loading...</option>
          )}
        </select>
      </div>

      <button
        type="button" // Important for forms
        onClick={handleVoiceToggle}
        disabled={disabled || !initialLanguageFetched || state.isProcessing} // Disable while processing too
        title={getButtonTitle()}
        className={`
          flex items-center justify-center w-12 h-12 rounded-full text-white transition-all duration-200
          focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500
          ${getButtonColor()}
          ${(disabled || !initialLanguageFetched) ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
          ${state.isRecording ? 'scale-110' : 'hover:scale-105'}
        `}
      >
        {getButtonIcon()}
      </button>

      {/* Status Messages */}
      {state.isRecording && (
        <div className="text-sm text-red-600 font-medium">
          🎤 Recording...
        </div>
      )}
      {state.isProcessing && (
        <div className="text-sm text-yellow-700 font-medium">
          🔄 Processing audio...
        </div>
      )}
      {state.error && (
        <div className="text-sm text-red-700 bg-red-100 border border-red-300 rounded-md px-3 py-2 max-w-xs text-center shadow">
          <span role="img" aria-label="error">❌</span> {state.error}
          <button
            onClick={clearError}
            className="ml-2 text-xs text-red-700 hover:text-red-900 underline font-semibold"
          >
            DISMISS
          </button>
        </div>
      )}
    </div>
  );
};
