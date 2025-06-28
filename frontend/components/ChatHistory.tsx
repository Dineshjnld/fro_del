import React, { useRef, useEffect } from 'react';
import type { Message } from '../types';
import { UserIcon } from './icons/UserIcon';
import { PoliceIcon } from './icons/PoliceIcon';
import { CodeIcon } from './icons/CodeIcon';
import { SpinnerIcon } from './icons/SpinnerIcon';

const MessageBubble: React.FC<{ message: Message }> = ({ message }) => {
  const isUser = message.sender === 'user';

  const getIcon = () => {
    if (isUser) return <UserIcon />;
    if (message.type === 'sql') return <CodeIcon />;
    if (message.type === 'status') return <SpinnerIcon />;
    return <PoliceIcon />;
  }

  const renderContent = () => {
    switch (message.type) {
      case 'sql':
        return (
          <div className="bg-gray-800 text-white p-4 rounded-lg font-mono text-sm shadow-inner">
            <p className="text-gray-300 italic mb-2">{message.summary}</p>
            <pre className="whitespace-pre-wrap overflow-x-auto"><code>{message.content}</code></pre>
          </div>
        );
      case 'status':
        return (
          <div className="flex items-center space-x-2 text-gray-500 italic">
            <SpinnerIcon />
            <span>{message.content}</span>
          </div>
        )
      case 'error':
        return <p className="text-red-600">{message.content}</p>;
      default:
        return <p>{message.content}</p>;
    }
  };

  return (
    <div className={`flex items-start space-x-4 py-4 ${isUser ? 'justify-end' : ''}`}>
      {!isUser && (
        <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center ${message.type === 'status' ? 'bg-transparent text-gray-500' : 'bg-blue-600 text-white'}`}>
          {getIcon()}
        </div>
      )}
      <div className={`max-w-xl rounded-lg px-4 py-3 ${isUser ? 'bg-blue-500 text-white' : 'bg-white text-gray-800 shadow-sm'}`}>
        {renderContent()}
      </div>
      {isUser && (
        <div className="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center bg-gray-700 text-white">
          <UserIcon />
        </div>
      )}
    </div>
  );
};

export const ChatHistory: React.FC<{ messages: Message[] }> = ({ messages }) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 bg-gray-100">
      <div className="max-w-4xl mx-auto">
        {messages.map((msg, index) => (
          <MessageBubble key={index} message={msg} />
        ))}
      </div>
    </div>
  );
};
