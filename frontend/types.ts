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
