import React, { useState, useEffect, useRef } from 'react';
import type { Status } from '../types';
import { VoiceInput } from './VoiceInput';
import { SendIcon } from './icons/SendIcon';

interface QueryInputProps {
  onSubmit: (query: string) => void;
  status: Status;
}

export const QueryInput: React.FC<QueryInputProps> = ({ onSubmit, status }) => {
  const [query, setQuery] = useState('');
  const [showVoiceInput, setShowVoiceInput] = useState(false);
  const [voiceAvailable, setVoiceAvailable] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    // Check if voice service is available
    fetch('http://127.0.0.1:8000/api/voice/status')
      .then(res => res.json())
      .then(data => {
        setVoiceAvailable(data.available);
      })
      .catch(() => {
        setVoiceAvailable(false);
      });
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSubmit(query);
      setQuery('');
    }
  };

  const handleVoiceTranscription = (text: string) => {
    setQuery(text);
    setShowVoiceInput(false);
    // Auto-submit after voice input
    setTimeout(() => {
      onSubmit(text);
    }, 500);
  };

  const isLoading = status === 'loading';

  return (
    <div className="bg-white border-t border-gray-200 px-6 py-4">
      <div className="max-w-4xl mx-auto">
        {/* Voice Input Modal */}
        {showVoiceInput && (
          <div className="mb-4 p-4 bg-gray-50 border border-gray-200 rounded-lg">
            <div className="flex justify-between items-center mb-3">
              <h3 className="text-lg font-medium text-gray-900">Voice Input</h3>
              <button
                onClick={() => setShowVoiceInput(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                ✕
              </button>
            </div>
            <VoiceInput 
              onTranscription={handleVoiceTranscription}
              disabled={isLoading}
            />
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex items-end space-x-4">
          {/* Voice Button */}
          {voiceAvailable && (
            <button
              type="button"
              onClick={() => setShowVoiceInput(!showVoiceInput)}
              disabled={isLoading}
              className={`
                flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center transition-colors duration-200
                ${showVoiceInput 
                  ? 'bg-red-500 text-white hover:bg-red-600' 
                  : 'bg-blue-600 text-white hover:bg-blue-700'
                }
                disabled:bg-gray-300 disabled:cursor-not-allowed
              `}
              title={showVoiceInput ? 'Close voice input' : 'Open voice input'}
            >
              {showVoiceInput ? '✕' : '🎤'}
            </button>
          )}

          {/* Text Input */}
          <div className="relative flex-1">
            <textarea
              ref={textareaRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={
                voiceAvailable 
                  ? "Type your query or use voice input...\n\nExamples:\n• Show me FIRs from Guntur district\n• How many arrests were made this month?\n• List officers in Krishna district"
                  : "Type your query...\n\nExamples:\n• Show me FIRs from Guntur district\n• How many arrests were made this month?\n• List officers in Krishna district"
              }
              disabled={isLoading}
              rows={4}
              className="w-full px-4 py-3 pr-12 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-shadow disabled:bg-gray-100 resize-none"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                  handleSubmit(e);
                }
              }}
            />
            <button
              type="submit"
              disabled={isLoading || !query.trim()}
              className="absolute right-2 bottom-2 w-8 h-8 flex items-center justify-center bg-blue-600 text-white rounded-full hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              <SendIcon />
            </button>
          </div>
        </form>

        {/* Status Messages */}
        <div className="mt-2 text-sm text-gray-500 flex items-center justify-between">
          <div>
            {voiceAvailable ? (
              <span>💡 Press Ctrl+Enter to submit, or use voice input for hands-free operation</span>
            ) : (
              <span>💡 Press Ctrl+Enter to submit</span>
            )}
          </div>
          {voiceAvailable && (
            <div className="text-xs text-green-600">
              🎤 Voice: IndicConformer + Whisper
            </div>
          )}
        </div>
      </div>
    </div>
  );
};