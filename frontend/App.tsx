import React, { useState, useEffect, useCallback } from 'react';
import { Header } from './components/Header';
import { ChatHistory } from './components/ChatHistory';
import { QueryInput } from './components/QueryInput';
import { ResultsDisplay } from './components/ResultsDisplay';
import { processQuery } from './services/apiService';
import type { Message, QueryResult, Status } from './types';

const App: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [queryResult, setQueryResult] = useState<QueryResult | null>(null);
  const [status, setStatus] = useState<Status>('idle');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Initial welcome message
    setMessages([
      {
        sender: 'ai',
        type: 'text',
        content: 'Welcome to the CCTNS Copilot. I am now powered by an open-source model. How can I help you access crime data today?'
      }
    ]);
  }, []);

  const handleQuerySubmit = useCallback(async (query: string) => {
    if (!query.trim() || status === 'loading') return;

    setStatus('loading');
    setError(null);
    setQueryResult(null);

    const userMessage: Message = { sender: 'user', type: 'text', content: query };
    const statusMessage: Message = { sender: 'ai', type: 'status', content: 'Processing your request with the open-source model...' };
    
    setMessages(prev => [...prev, userMessage, statusMessage]);

    try {
      const response = await processQuery(query);
      
      const aiSqlMessage: Message = { sender: 'ai', type: 'sql', content: response.sql, summary: response.summary };
      setQueryResult(response.result);

      // Replace status message with the final SQL message
      setMessages(prev => [...prev.slice(0, -1), aiSqlMessage]);

    } catch (e) {
      console.error(e);
      const errorMessage = e instanceof Error ? e.message : 'An unknown error occurred.';
      setError(`Failed to process your request. ${errorMessage}`);
      const aiErrorMessage: Message = { sender: 'ai', type: 'error', content: `I'm sorry, I encountered an error: ${errorMessage}` };
      
      // Replace status message with the error message
      setMessages(prev => [...prev.slice(0, -1), aiErrorMessage]);
    } finally {
      setStatus('idle');
    }
  }, [status]);

  return (
    <div className="flex flex-col h-screen font-sans bg-gray-50">
      <Header />
      <main className="flex-1 overflow-hidden flex">
        <div className="flex-1 flex flex-col overflow-hidden">
          <ChatHistory messages={messages} />
          {error && <div className="px-4 py-2 text-red-700 bg-red-100 border-t border-red-200">{error}</div>}
          <QueryInput onSubmit={handleQuerySubmit} status={status} />
        </div>
        <ResultsDisplay result={queryResult} status={status} />
      </main>
    </div>
  );
};

export default App;
