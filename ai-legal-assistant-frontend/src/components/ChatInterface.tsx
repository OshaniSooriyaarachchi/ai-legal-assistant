import React, { useState, useRef, useEffect } from 'react';
import { useAppDispatch, useAppSelector } from '../app/hooks';
import { sendMessage, clearChatLocal, clearChatHistory, uploadDocument } from '../features/chat/chatSlice';
import MessageBubble from './MessageBubble';

const ChatInterface: React.FC = () => {
  const dispatch = useAppDispatch();
  const { messages, loading, uploadedDocuments, currentSessionId, isClearingHistory } = useAppSelector((state) => state.chat);
  const [input, setInput] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const isSubmittingRef = useRef(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleClearChat = async () => {
    if (currentSessionId) {
      // If there's a current session, clear history from database
      if (window.confirm('Are you sure you want to clear this chat?')) {
        try {
          await dispatch(clearChatHistory(currentSessionId)).unwrap();
        } catch (error) {
          console.error('Failed to clear chat history:', error);
          alert('Failed to clear chat history. Please try again.');
        }
      }
    } else {
      // If no session, just clear local messages
      dispatch(clearChatLocal());
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    // Prevent double submission
    if ((!input.trim() && selectedFiles.length === 0) || loading || isSubmittingRef.current) return;
    
    isSubmittingRef.current = true;

    try {
      // Handle file uploads first
      if (selectedFiles.length > 0) {
        for (const file of selectedFiles) {
          try {
            await dispatch(uploadDocument(file)).unwrap();
          } catch (error) {
            console.error('Failed to upload document:', error);
          }
        }
        setSelectedFiles([]);
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
      }

      // Then handle text message if any
      if (input.trim()) {
        const userMessage = input.trim();
        setInput(''); // Clear input immediately to prevent double submission

        try {
          await dispatch(sendMessage(userMessage)).unwrap();
        } catch (error) {
          console.error('Failed to send message:', error);
        }
      }
    } finally {
      isSubmittingRef.current = false;
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files);
      // Filter for allowed file types
      const allowedTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'];
      const validFiles = files.filter(file => 
        allowedTypes.includes(file.type) && file.size <= 10 * 1024 * 1024 // 10MB limit
      );
      setSelectedFiles(prev => [...prev, ...validFiles]);
    }
  };

  const removeFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const triggerFileInput = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="flex flex-col h-full border-l border-gray-300">
      {/* Chat Header */}
      <div className="bg-blue-600 text-white p-4 flex justify-between items-center">
        <h3 className="font-semibold">AI Legal Assistant</h3>
        <div className="flex space-x-2">
          {uploadedDocuments.length > 0 && (
            <span className="text-blue-200 text-sm">
              {uploadedDocuments.length} document{uploadedDocuments.length > 1 ? 's' : ''} uploaded
            </span>
          )}
          <button
            onClick={handleClearChat}
            disabled={isClearingHistory}
            className="text-blue-200 hover:text-white text-sm disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
          >
            {isClearingHistory ? (
              <>
                <svg className="w-3 h-3 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Clearing...
              </>
            ) : (
              'Clear Chat'
            )}
          </button>
        </div>
      </div>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 py-8">
            <p>Ask me anything about legal matters!</p>
            <p className="text-sm mt-2">You can upload documents and ask questions about them.</p>
          </div>
        )}
        
        {messages.map((message, index) => (
          <MessageBubble key={index} message={message} />
        ))}
        
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg p-3 max-w-xs">
              <div className="flex space-x-2">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Selected Files Display */}
      {selectedFiles.length > 0 && (
        <div className="px-4 py-2 border-t border-gray-200 bg-gray-50">
          <div className="flex flex-wrap gap-2">
            {selectedFiles.map((file, index) => (
              <div key={index} className="flex items-center bg-blue-100 rounded-lg px-3 py-1 text-sm">
                <span className="truncate max-w-32">{file.name}</span>
                <button
                  onClick={() => removeFile(index)}
                  className="ml-2 text-red-500 hover:text-red-700"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-gray-200">
        <div className="flex space-x-2">
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.docx,.txt"
            onChange={handleFileSelect}
            className="hidden"
          />
          <button
            type="button"
            onClick={triggerFileInput}
            className="flex-shrink-0 bg-gray-100 text-gray-600 px-3 py-2 rounded-lg hover:bg-gray-200 border border-gray-300"
            disabled={loading}
          >
            📎
          </button>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a legal question or upload documents..."
            className="flex-1 border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || (!input.trim() && selectedFiles.length === 0)}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
};

export default ChatInterface;