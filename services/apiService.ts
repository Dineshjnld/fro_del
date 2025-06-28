import type { QueryResult, Message } from '../types'; // Assuming types.ts will be in root

const API_BASE_URL = 'http://127.0.0.1:8000'; // Ensure this is correct for your setup

export interface BackendProcessedQueryResponse {
  query: string;
  sql: string;
  results: { // This structure is based on api/main.py's process_query
    success: boolean;
    row_count?: number;
    execution_time?: number;
    data?: QueryResult['data']; // Assuming QueryResult has { columns: string[], rows: any[][] }
    error?: string;
    columns?: string[]; // if data is not nested under a QueryResult like object
  };
  summary?: string; // If backend provides summary
  success: boolean; // Overall success of the operation from backend
  error?: string;
  suggestion?: string;
}

// This function will call your FastAPI backend
export const processQueryWithBackend = async (queryText: string): Promise<BackendProcessedQueryResponse> => {
  const response = await fetch(`${API_BASE_URL}/api/query/process`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ text: queryText }), // api/main.py expects {"text": "..."}
  });

  if (!response.ok) {
    // Try to parse error from backend, otherwise throw generic error
    let errorDetail = `Server responded with status ${response.status}`;
    try {
      const errorData = await response.json();
      errorDetail = errorData.detail || errorData.error || errorDetail;
    } catch (e) {
      // Ignore if error response is not JSON
    }
    throw new Error(errorDetail);
  }

  const data = await response.json();
  // Ensure the data matches BackendProcessedQueryResponse structure
  // The actual structure from api/main.py process_query is:
  // {"query": text, "sql": sql_result["sql"], "results": execution_result, "success": True}
  // or {"error": "...", "suggestion": "..."}
  return data;
};
