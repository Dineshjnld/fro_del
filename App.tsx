import React, { useState, useEffect, useCallback } from 'react';
import { Header } from './components/Header';
import { ChatHistory } from './components/ChatHistory';
import { QueryInput } from './components/QueryInput';
import { ResultsDisplay } from './components/ResultsDisplay';
import { VoiceInput } from './components/VoiceInput'; // Import VoiceInput
import { processQueryWithBackend } from './services/apiService'; // Import backend service
import type { Message, QueryResult, Status } from './types';

const App: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [queryResult, setQueryResult] = useState<QueryResult | null>(null);
  const [status, setStatus] = useState<Status>('idle');
  const [error, setError] = useState<string | null>(null);
  // chatRef and initChat related to @google/genai are removed

  useEffect(() => {
    // Simplified initial message
    setMessages([
      {
        sender: 'ai',
        type: 'text',
        content: 'Welcome to the CCTNS Copilot. How can I help you today? Type your query or use the voice input.'
      }
    ]);
  }, []);

  const handleQuerySubmit = useCallback(async (query: string) => {
    if (!query.trim()) return;

    setStatus('loading');
    setError(null);
    // setQueryResult(null); // Keep previous results visible while loading new ones for better UX

    const userMessage: Message = { sender: 'user', type: 'text', content: query };
    setMessages(prev => [...prev, userMessage]);

    try {
      setMessages(prev => [...prev, { sender: 'ai', type: 'status', content: 'Processing your request...' }]);
      
      const backendResponse = await processQueryWithBackend(query);

      // Remove the "Processing..." status message
      setMessages(prev => prev.filter(msg => !(msg.type === 'status' && msg.sender === 'ai')));

      if (backendResponse.success && backendResponse.sql && backendResponse.results) {
        const aiSqlMessage: Message = {
          sender: 'ai',
          type: 'sql',
          content: backendResponse.sql,
          summary: backendResponse.summary || `Found ${backendResponse.results.row_count || 0} results.`
        };
        setMessages(prev => [...prev, aiSqlMessage]);

        // Transform backend results to QueryResult format
        const newQueryResult: QueryResult = {
          columns: backendResponse.results.columns || (backendResponse.results.data && backendResponse.results.data.length > 0 ? Object.keys(backendResponse.results.data[0]) : []),
          rows: backendResponse.results.data || [],
          query: backendResponse.sql,
        };
        setQueryResult(newQueryResult);

      } else {
        // Handle errors or cases where SQL/results might not be present
        const errorMessageContent = backendResponse.error || backendResponse.suggestion || 'Sorry, I could not process that request.';
        setError(errorMessageContent);
        const aiErrorMessage: Message = { sender: 'ai', type: 'error', content: errorMessageContent };
        setMessages(prev => [...prev, aiErrorMessage]);
        setQueryResult(null); // Clear previous results on error
      }

    } catch (e) {
      console.error(e);
      const errorMessage = e instanceof Error ? e.message : 'An unknown error occurred.';
      setError(`Failed to process your request: ${errorMessage}`);
      const aiErrorMessage: Message = { sender: 'ai', type: 'error', content: `I'm sorry, I encountered an error: ${errorMessage}` };
      // Ensure status message is removed before adding error message
      setMessages(prev => [...prev.filter(msg => !(msg.type === 'status' && msg.sender === 'ai')), aiErrorMessage]);
      setQueryResult(null); // Clear previous results on error
    } finally {
      setStatus('idle');
    }
  }, []);

  const handleTranscription = (transcribedText: string) => {
    if (transcribedText) {
      // Optionally, add the transcribed text as a user message before submitting
      // const userMessage: Message = { sender: 'user', type: 'text', content: transcribedText };
      // setMessages(prev => [...prev, userMessage]);
      handleQuerySubmit(transcribedText);
    }
  };

  return (
    <div className="flex flex-col h-screen font-sans bg-gray-50 text-gray-800">
      <Header />
      <main className="flex-1 overflow-hidden flex flex-col md:flex-row">
        <div className="flex-1 flex flex-col overflow-hidden p-4 space-y-4">
          <ChatHistory messages={messages} />
          {error && (
            <div className="px-4 py-3 text-red-700 bg-red-100 border border-red-300 rounded-md shadow-sm">
              <strong>Error:</strong> {error}
            </div>
          )}
           {/* Voice Input Component */}
          <VoiceInput onTranscription={handleTranscription} disabled={status === 'loading'} />
          <QueryInput onSubmit={handleQuerySubmit} status={status} />
        </div>
        <ResultsDisplay result={queryResult} status={status} />
      </main>
    </div>
  );
};

export default App;
