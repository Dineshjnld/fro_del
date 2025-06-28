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
  query: string;
}

export type Status = 'idle' | 'listening' | 'loading' | 'error';

// Voice-related types
export interface VoiceTranscriptionResult {
  text: string;
  confidence: number;
  language: string;
  modelUsed: string;
  enhanced?: {
    enhancedText: string;
    corrections: string[];
    confidence: number;
  };
}

export interface VoiceRecordingState {
  isRecording: boolean;
  isProcessing: boolean;
  error: string | null;
  language: string;
}