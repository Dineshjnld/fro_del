import type { VoiceTranscriptionResult } from '../types'; // Assuming types.ts will be in root

const API_BASE_URL = 'http://127.0.0.1:8000'; // Ensure this is correct

export interface VoiceServiceConfig {
  language: string;
  enhanceText: boolean;
}

export const transcribeAudio = async (
  audioBlob: Blob,
  config: VoiceServiceConfig = { language: 'te', enhanceText: true } // Default language 'te'
): Promise<VoiceTranscriptionResult> => {

  const formData = new FormData();
  // Ensure the filename is what the backend expects, or just a generic one.
  // 'audio.wav' might be okay, but some backends might infer type from it.
  // Sending as 'audio.webm' if that's the recording format.
  let filename = 'audio.wav'; // Default
  if (audioBlob.type.includes('webm')) {
    filename = 'audio.webm';
  } else if (audioBlob.type.includes('mp4')) {
    filename = 'audio.mp4';
  } else if (audioBlob.type.includes('mpeg')) {
    filename = 'audio.mp3';
  }


  formData.append('file', audioBlob, filename);
  formData.append('language', config.language);
  // Backend `backend/main.py` expects 'enhance_text' not 'enhanceText'
  // And it expects a string 'true' or 'false'.
  // The `api/main.py` (target) will need to be checked for this param if we merge.
  // For now, let's assume `api/main.py`'s /api/voice/transcribe will take 'language' and 'file'.
  // The enhance_text is more from the `backend/main.py` version.
  // Let's check what `api/main.py`'s transcribe endpoint expects.
  // `api/main.py`'s /api/voice/transcribe takes `file: UploadFile` and `language: str`. No enhance_text.
  // So, I will remove `enhance_text` for now from FormData.

  const response = await fetch(`${API_BASE_URL}/api/voice/transcribe?language=${config.language}`, {
    method: 'POST',
    body: formData,
    // Note: When sending FormData, don't set 'Content-Type' header.
    // The browser will set it correctly with the boundary.
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Failed to transcribe audio' }));
    throw new Error(errorData.detail || `Server responded with status ${response.status}`);
  }

  const result = await response.json();

  // The structure from `api/main.py`'s stt_processor mock is:
  // {"text": ..., "confidence": ..., "language": ..., "model_used": ...}
  // The structure from `backend/main.py` (which is more detailed and preferred) is:
  // {"success": True, "transcription": {"text": ..., "confidence": ..., "language": ..., "model_used": ...}, ...}
  // Assuming we're aiming for the more detailed one after merging backend logic into api/main.py:
  if (result.success === false || (result.success && !result.transcription)) { // Check for explicit failure or missing transcription
     throw new Error(result.error || result.message || 'Transcription failed or no text found');
  }

  // If `api/main.py` directly returns the simpler structure (from current mock):
  // return {
  //   text: result.text,
  //   confidence: result.confidence,
  //   language: result.language,
  //   modelUsed: result.model_used,
  // };

  // Assuming the richer response structure from backend/main.py will be in api/main.py:
   return {
    text: result.transcription.text,
    confidence: result.transcription.confidence,
    language: result.transcription.language,
    modelUsed: result.transcription.model_used,
    enhanced: result.enhancement ? { // if enhancement is part of the final merged backend
      enhancedText: result.enhancement.enhanced_text,
      corrections: result.enhancement.corrections_applied,
      // confidence: result.enhancement.confidence // This might not exist, adapt as per actual backend
    } : undefined
  };
};

export const getSupportedLanguagesFromBackend = async () => {
  // Assuming api/main.py will have an endpoint like this, similar to backend/main.py
  const response = await fetch(`${API_BASE_URL}/api/voice/languages`);

  if (!response.ok) {
    throw new Error('Failed to fetch supported languages');
  }
  const data = await response.json();
  return data.languages || []; // E.g. { languages: [{code, name, native_name}, ...]}
};

// Voice status endpoint might also be useful
export const getVoiceProcessingStatus = async () => {
  const response = await fetch(`${API_BASE_URL}/api/voice/status`);
  if (!response.ok) {
    throw new Error('Failed to fetch voice status');
  }
  return await response.json();
};
