import React from 'react';
import ReactMarkdown from 'react-markdown';
import type { Components } from 'react-markdown';

interface Message {
  id: string;
  content: string;
  sender: 'user' | 'assistant';
  timestamp: string;
  type?: 'text' | 'document';
  fileName?: string;
}

interface MessageBubbleProps {
  message: Message;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.sender === 'user';
  const isDocument = message.type === 'document';

  // Custom components for markdown rendering with correct typing
  const markdownComponents: Components = {
    // Custom paragraph component for justified text
    p: ({ children }) => (
      <p className="mb-3 last:mb-0 text-justify leading-relaxed">
        {children}
      </p>
    ),
    // Custom strong (bold) component
    strong: ({ children }) => (
      <strong className="font-semibold text-gray-900">
        {children}
      </strong>
    ),
    // Custom emphasis (italic) component
    em: ({ children }) => (
      <em className="italic">
        {children}
      </em>
    ),
    // Custom list components
    ul: ({ children }) => (
      <ul className="list-disc list-inside mb-3 space-y-1">
        {children}
      </ul>
    ),
    ol: ({ children }) => (
      <ol className="list-decimal list-inside mb-3 space-y-1">
        {children}
      </ol>
    ),
    li: ({ children }) => (
      <li className="text-justify">
        {children}
      </li>
    ),
    // Custom code components
    code: ({ children, className, ...props }) => {
      const isInline = !className || !className.includes('language-');
      
      if (isInline) {
        return (
          <code className="bg-gray-200 px-1 py-0.5 rounded text-sm font-mono" {...props}>
            {children}
          </code>
        );
      }
      return (
        <pre className="bg-gray-100 p-3 rounded-md overflow-x-auto mb-3">
          <code className="text-sm font-mono" {...props}>
            {children}
          </code>
        </pre>
      );
    },
    // Custom blockquote component
    blockquote: ({ children }) => (
      <blockquote className="border-l-4 border-gray-300 pl-4 italic mb-3">
        {children}
      </blockquote>
    ),
    // Custom heading components
    h1: ({ children }) => (
      <h1 className="text-xl font-bold mb-3 text-gray-900">
        {children}
      </h1>
    ),
    h2: ({ children }) => (
      <h2 className="text-lg font-bold mb-2 text-gray-900">
        {children}
      </h2>
    ),
    h3: ({ children }) => (
      <h3 className="text-base font-bold mb-2 text-gray-900">
        {children}
      </h3>
    ),
  };

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`max-w-2xl lg:max-w-3xl px-4 py-3 rounded-2xl ${
          isUser
            ? 'bg-blue-600 text-white ml-12'
            : isDocument
            ? 'bg-green-100 text-green-800 border border-green-200 mr-12'
            : 'bg-gray-100 text-gray-800 mr-12'
        }`}
      >
        {/* Message Content */}
        <div className="text-sm">
          {isUser || isDocument ? (
            // For user messages and documents, use simple text
            <p className="whitespace-pre-wrap leading-relaxed">
              {message.content}
            </p>
          ) : (
            // For assistant messages, use markdown rendering
            <ReactMarkdown components={markdownComponents}>
              {message.content}
            </ReactMarkdown>
          )}
        </div>
        
        {/* Timestamp */}
        <p className={`text-xs mt-2 ${
          isUser ? 'text-blue-100' : 'text-gray-500'
        }`}>
          {new Date(message.timestamp).toLocaleTimeString()}
        </p>
      </div>
    </div>
  );
};

export default MessageBubble;