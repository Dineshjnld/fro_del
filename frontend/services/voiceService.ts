import type { VoiceTranscriptionResult } from '../types';

const API_BASE_URL = 'http://127.0.0.1:8000';

export interface VoiceServiceConfig {
  language: string;
  enhanceText: boolean;
}

export const transcribeAudio = async (
  audioBlob: Blob, 
  config: VoiceServiceConfig = { language: 'te', enhanceText: true }
): Promise<VoiceTranscriptionResult> => {
  
  const formData = new FormData();
  formData.append('file', audioBlob, 'audio.wav');
  formData.append('language', config.language);
  formData.append('enhance_text', config.enhanceText.toString());

  const response = await fetch(`${API_BASE_URL}/api/voice/transcribe`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Failed to transcribe audio' }));
    throw new Error(errorData.detail || `Server responded with status ${response.status}`);
  }

  const result = await response.json();
  
  if (!result.success) {
    throw new Error(result.error || 'Transcription failed');
  }

  return {
    text: result.transcription.text,
    confidence: result.transcription.confidence,
    language: result.transcription.language,
    modelUsed: result.transcription.model_used,
    enhanced: result.enhancement ? {
      enhancedText: result.enhancement.enhanced_text,
      corrections: result.enhancement.corrections_applied,
      confidence: result.enhancement.confidence
    } : undefined
  };
};

export const getSupportedLanguages = async () => {
  const response = await fetch(`${API_BASE_URL}/api/voice/languages`);
  
  if (!response.ok) {
    throw new Error('Failed to fetch supported languages');
  }
  
  return await response.json();
};

export const getVoiceStatus = async () => {
  const response = await fetch(`${API_BASE_URL}/api/voice/status`);
  
  if (!response.ok) {
    throw new Error('Failed to fetch voice status');
  }
  
  return await response.json();
};