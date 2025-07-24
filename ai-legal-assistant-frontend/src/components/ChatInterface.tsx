import React, { useState, useRef, useEffect } from 'react';
import { useAppDispatch, useAppSelector } from '../app/hooks';
import { sendMessage, clearChatLocal, clearChatHistory, uploadDocument } from '../features/chat/chatSlice';
import { RateLimitError } from '../services/api';
import MessageBubble from './MessageBubble';

interface RateLimitModalProps {
  isOpen: boolean;
  onClose: () => void;
  errorDetail: any;
}

const RateLimitModal: React.FC<RateLimitModalProps> = ({ isOpen, onClose, errorDetail }) => {
  if (!isOpen) return null;

  const isExpired = errorDetail?.error === 'SUBSCRIPTION_EXPIRED';
  const isInactive = errorDetail?.error === 'SUBSCRIPTION_INACTIVE';
  const isLimitExceeded = errorDetail?.error === 'DAILY_LIMIT_EXCEEDED';

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg max-w-md w-full mx-4 p-6">
        <div className="flex items-center mb-4">
          <div className="rounded-full bg-red-100 p-2 mr-3">
            <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-900">
            {isLimitExceeded ? 'Daily Limit Reached' : 
             isExpired ? 'Subscription Expired' : 
             isInactive ? 'Subscription Inactive' : 'Query Limit Reached'}
          </h3>
        </div>
        
        <div className="mb-6">
          <p className="text-gray-600 mb-4">
            {errorDetail?.message || 'You have reached your query limit.'}
          </p>
          
          {isLimitExceeded && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
              <div className="flex justify-between items-center text-sm">
                <span className="text-yellow-800">Today's usage:</span>
                <span className="font-semibold text-yellow-900">
                  {errorDetail?.current_usage} / {errorDetail?.daily_limit}
                </span>
              </div>
              <div className="w-full bg-yellow-200 rounded-full h-2 mt-2">
                <div 
                  className="bg-yellow-600 h-2 rounded-full" 
                  style={{ 
                    width: `${Math.min((errorDetail?.current_usage / errorDetail?.daily_limit) * 100, 100)}%` 
                  } as React.CSSProperties}
                ></div>
              </div>
            </div>
          )}
          
          <div className="text-sm text-gray-500">
            <p className="font-medium mb-2">Upgrade to continue:</p>
            <ul className="space-y-1">
              <li>• Unlimited daily queries</li>
              <li>• Priority support</li>
              <li>• Advanced features</li>
              <li>• No interruptions</li>
            </ul>
          </div>
        </div>
        
        <div className="flex space-x-3">
          <button
            onClick={() => {
              onClose();
              // Navigate to subscription page
              window.location.href = '/subscription';
            }}
            className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 font-medium"
          >
            Upgrade Now
          </button>
          <button
            onClick={onClose}
            className="flex-1 bg-gray-100 text-gray-700 py-2 px-4 rounded-lg hover:bg-gray-200 font-medium"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

const ChatInterface: React.FC = () => {
  const dispatch = useAppDispatch();
  const { messages, loading, uploadedDocuments, currentSessionId, isClearingHistory, error } = useAppSelector((state) => state.chat);
  const [input, setInput] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [showRateLimitModal, setShowRateLimitModal] = useState(false);
  const [rateLimitError, setRateLimitError] = useState<any>(null);
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
        } catch (error: any) {
          console.error('Failed to send message:', error);
          
          // Check if it's a rate limit error
          if (error instanceof RateLimitError || 
              (error.response && error.response.status === 429) ||
              (error.message && error.message.includes('rate limit')) ||
              (error.detail && ['DAILY_LIMIT_EXCEEDED', 'SUBSCRIPTION_EXPIRED', 'SUBSCRIPTION_INACTIVE'].includes(error.detail.error))) {
            
            setRateLimitError(error.detail || error);
            setShowRateLimitModal(true);
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
        isOpen={showRateLimitModal}
        onClose={() => {
          setShowRateLimitModal(false);
          setRateLimitError(null);
        }}
        errorDetail={rateLimitError}
      />
      
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
    </>
  );
};

export default ChatInterface;