import type { QueryResult } from '../types';

const API_BASE_URL = 'http://127.0.0.1:8000';

export interface ProcessedQueryResponse {
  sql: string;
  summary: string;
  result: QueryResult;
  error?: string;
}

export const processQuery = async (query: string): Promise<ProcessedQueryResponse> => {
  const response = await fetch(`${API_BASE_URL}/process-query`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ query }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Failed to fetch from backend.' }));
    throw new Error(errorData.detail || `Server responded with status ${response.status}`);
  }
  
  const data = await response.json();
  if (data.error) {
     throw new Error(data.error);
  }

  return data;
};
