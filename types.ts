export type Sender = 'user' | 'ai';

export type MessageType = 'text' | 'sql' | 'error' | 'status';

export interface Message {
  sender: Sender;
  type: MessageType;
  content: string;
  summary?: string;
}

export interface QueryResult {
  columns: string[];
  rows: (string | number)[][];
  query: string; // The original SQL query that produced this result
}

export type Status = 'idle' | 'listening' | 'loading' | 'error';

// Voice-related types
export interface VoiceTranscriptionResult {
  text: string;
  confidence?: number; // Made optional as not all models provide it easily
  language: string;
  modelUsed?: string; // Optional
  enhanced?: {
    enhancedText: string;
    corrections: string[];
    confidence?: number; // Optional
  };
}

export interface VoiceRecordingState {
  isRecording: boolean;
  isProcessing: boolean;
  error: string | null;
  language: string; // e.g., 'en', 'te', 'hi'
}

// For supported languages list from backend
export interface Language {
  code: string;       // e.g., "en", "te"
  name: string;       // e.g., "English", "Telugu"
  native_name: string; // e.g., "English", "తెలుగు"
  optimized?: boolean;
}
