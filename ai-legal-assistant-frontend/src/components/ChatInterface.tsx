import React, { useState, useRef, useEffect } from 'react';
import { useAppDispatch, useAppSelector } from '../app/hooks';
import { sendMessage, clearChatLocal, clearChatHistory, uploadDocument, clearRateLimitError } from '../features/chat/chatSlice';
import { RateLimitError } from '../services/api';
import MessageBubble from './MessageBubble';
import { useSelector, useDispatch } from 'react-redux';
import RateLimitModal from './RateLimitModal';
import { UserTypeSelector } from './UserTypeSelector';
import { useUserTypeContext } from '../contexts/UserTypeContext';

const ChatInterface: React.FC = () => {
  const dispatch = useDispatch();
  const { rateLimitError, rateLimitErrorData } = useSelector((state: any) => state.chat);
  const appDispatch = useAppDispatch();
  const { messages, loading, uploadedDocuments, currentSessionId, isClearingHistory, error } = useAppSelector((state) => state.chat);
  const { userType } = useUserTypeContext();
  const [input, setInput] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [showRateLimitModal, setShowRateLimitModal] = useState(false);
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
          await appDispatch(clearChatHistory(currentSessionId)).unwrap();
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
            // For chat uploads, use filename as display name and auto-generate description
            const displayName = file.name.replace(/\.[^/.]+$/, '');
            const description = `Document uploaded to chat session: ${file.name}`;
            await appDispatch(uploadDocument({ file, displayName, description })).unwrap();
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
          await appDispatch(sendMessage({ query: userMessage, userType })).unwrap();
        } catch (error: any) {
          console.error('Failed to send message:', error);
          
          // Check if it's a rate limit error
          if (error instanceof RateLimitError || 
              (error.response && error.response.status === 429) ||
              (error.message && error.message.includes('rate limit')) ||
              (error.detail && ['DAILY_LIMIT_EXCEEDED', 'SUBSCRIPTION_EXPIRED', 'SUBSCRIPTION_INACTIVE'].includes(error.detail.error))) {
            
            // Rate limit error will be handled by Redux state
            console.log('Rate limit error detected:', error);
          } else {
            // Handle other errors
            console.error('Chat error:', error);
          }
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
    <>
      <RateLimitModal
        isOpen={rateLimitError}
        onClose={() => dispatch(clearRateLimitError())}
        usageInfo={rateLimitErrorData}
        onUpgrade={(planName: string) => {
          // Handle upgrade logic here
          console.log('Upgrade to:', planName);
        }}
      />
      
      <div className="flex flex-col h-full">
      {/* Chat Header */}
      <div className="bg-blue-600 text-white p-4 flex justify-between items-center flex-shrink-0">
        <h3 className="font-semibold">AI Legal Assistant</h3>
        
        {/* User Type Selector */}
        <div className="flex-1 flex justify-center">
          <UserTypeSelector />
        </div>
        
        <div className="flex space-x-2">{uploadedDocuments.length > 0 && (
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
      <div className="flex-1 overflow-y-auto p-6 bg-gray-50">
        <div className="max-w-4xl mx-auto">
          {messages.length === 0 && (
            <div className="text-center text-gray-500 py-12">
              <div className="bg-white rounded-xl p-8 shadow-sm">
                <h3 className="text-xl font-semibold text-gray-700 mb-2">
                  Welcome to AI Legal Assistant
                </h3>
                <p className="text-gray-600 mb-4">
                  Ask me anything about legal matters!
                </p>
                <p className="text-sm text-gray-500">
                  You can upload documents and ask questions about them.
                </p>
              </div>
            </div>
          )}
          
          {messages.map((message, index) => (
            <MessageBubble key={index} message={message} />
          ))}
          
          {loading && (
            <div className="flex justify-start mb-4">
              <div className="bg-white rounded-2xl p-4 max-w-xs mr-12 shadow-sm">
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
      </div>

      {/* Selected Files Display */}
      {selectedFiles.length > 0 && (
        <div className="px-6 py-3 border-t border-gray-200 bg-gray-50 flex-shrink-0">
          <div className="max-w-4xl mx-auto">
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
        </div>
      )}

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="p-6 bg-white border-t border-gray-200 flex-shrink-0">
        <div className="max-w-4xl mx-auto">
          <div className="flex space-x-3">
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
              className="flex-shrink-0 bg-gray-100 text-gray-600 px-4 py-3 rounded-xl hover:bg-gray-200 border border-gray-300 transition-colors"
              disabled={loading}
            >
              📎
            </button>
            <div className="flex-1 relative">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask a legal question or upload documents..."
                className="w-full border border-gray-300 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={loading}
              />
            </div>
            <button
              type="submit"
              disabled={loading || (!input.trim() && selectedFiles.length === 0)}
              className="bg-blue-600 text-white px-6 py-3 rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
            >
              Send
            </button>
          </div>
        </div>
      </form>
    </div>
    </>
  );
};

export default ChatInterface;