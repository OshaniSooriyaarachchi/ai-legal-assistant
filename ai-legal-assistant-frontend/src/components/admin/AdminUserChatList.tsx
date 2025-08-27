import React, { useState, useEffect } from 'react';
import { api } from '../../services/api';

interface ChatSession {
  session_id: string;
  title: string;
  user_id: string;
  user_email: string;
  created_at: string;
  updated_at: string;
}

interface ChatHistory {
  id: string;
  query_text: string;
  response_text: string;
  gemini_prompt?: string;         // NEW: For admin viewing
  gemini_raw_response?: string;   // NEW: For admin viewing
  message_type: string;
  created_at: string;
  document_ids?: string[];
}

interface AdminPromptSectionProps {
  title: string;
  content: string;
  bgColor: string;
  textColor: string;
  headerColor: string;
}

const AdminPromptSection: React.FC<AdminPromptSectionProps> = ({ 
  title, content, bgColor, textColor, headerColor 
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className={`${bgColor} p-3 rounded-lg`}>
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={`${headerColor} font-medium text-sm mb-1 flex items-center w-full text-left hover:opacity-80`}
      >
        <span className="mr-2">{isExpanded ? '▼' : '▶'}</span>
        {title}
        <span className="text-xs ml-2 opacity-70">
          ({content.length} characters)
        </span>
      </button>
      
      {isExpanded && (
        <div className={`${textColor} mt-2`}>
          <pre className="whitespace-pre-wrap text-sm max-h-96 overflow-y-auto bg-white bg-opacity-50 p-2 rounded border">
            {content}
          </pre>
        </div>
      )}
    </div>
  );
};

const AdminUserChatList: React.FC = () => {
  const [chats, setChats] = useState<ChatSession[]>([]);
  const [selectedChat, setSelectedChat] = useState<ChatSession | null>(null);
  const [chatHistory, setChatHistory] = useState<ChatHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterUser, setFilterUser] = useState('');

  useEffect(() => {
    fetchAllChats();
  }, []);

  const fetchAllChats = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.get('/admin/users/chats');
      setChats(response.data.chats);
    } catch (err: any) {
      console.error('Failed to fetch chats:', err);
      setError(err.response?.data?.detail || 'Failed to fetch chats');
    } finally {
      setLoading(false);
    }
  };

  const fetchChatHistory = async (sessionId: string) => {
    try {
      setHistoryLoading(true);
      const response = await api.get(`/admin/sessions/${sessionId}/history`);
      setChatHistory(response.data.history);
    } catch (err: any) {
      console.error('Failed to fetch chat history:', err);
      setError(err.response?.data?.detail || 'Failed to fetch chat history');
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleChatSelect = (chat: ChatSession) => {
    setSelectedChat(chat);
    setChatHistory([]);
    fetchChatHistory(chat.session_id);
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return 'Unknown';
    
    try {
      let date;
      
      // Handle different date formats and ensure proper parsing
      if (dateString.includes('T')) {
        // ISO format - ensure it has timezone info
        if (!dateString.endsWith('Z') && !dateString.includes('+')) {
          // Assume UTC if no timezone specified
          date = new Date(dateString + 'Z');
        } else {
          date = new Date(dateString);
        }
      } else {
        // If no time part, assume it's a date only and add UTC time
        date = new Date(dateString + 'T00:00:00Z');
      }
      
      // Check if date is valid
      if (isNaN(date.getTime())) {
        // Try parsing without timezone modifications
        date = new Date(dateString);
        if (isNaN(date.getTime())) {
          return 'Invalid Date';
        }
      }
      
      // Get current time in Sri Lankan timezone for comparison
      const now = new Date();
      const sriLankanNow = new Date(now.toLocaleString("en-US", { timeZone: "Asia/Colombo" }));
      const sriLankanDate = new Date(date.toLocaleString("en-US", { timeZone: "Asia/Colombo" }));
      
      const diffInHours = (sriLankanNow.getTime() - sriLankanDate.getTime()) / (1000 * 60 * 60);
      
      // Show relative time for recent items
      if (Math.abs(diffInHours) < 24) {
        const timeString = sriLankanDate.toLocaleTimeString('en-US', {
          hour: '2-digit',
          minute: '2-digit',
          hour12: true
        });
        
        if (diffInHours >= 0 && diffInHours < 24) {
          return `${timeString} (today)`;
        } else if (diffInHours < 0 && diffInHours > -24) {
          return `${timeString} (today)`;
        }
      } else if (Math.abs(diffInHours) < 48) {
        const timeString = sriLankanDate.toLocaleTimeString('en-US', {
          hour: '2-digit',
          minute: '2-digit',
          hour12: true
        });
        return `${timeString} (yesterday)`;
      }
      
      // Show full date for older items
      return sriLankanDate.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: true
      });
      
    } catch (error) {
      console.error('Date formatting error:', error, 'for date:', dateString);
      return 'Invalid Date';
    }
  };

  const formatMessage = (text: string, maxLength: number = 100) => {
    return text.length > maxLength ? `${text.substring(0, maxLength)}...` : text;
  };

  const filteredChats = chats.filter(chat => {
    const matchesSearch = chat.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         chat.user_email.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesUser = !filterUser || chat.user_email.toLowerCase().includes(filterUser.toLowerCase());
    return matchesSearch && matchesUser;
  });

  const uniqueUsers = Array.from(new Set(chats.map(chat => chat.user_email))).sort();

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
        <strong className="font-bold">Error!</strong>
        <span className="block sm:inline"> {error}</span>
        <button
          onClick={fetchAllChats}
          className="mt-2 bg-red-500 hover:bg-red-700 text-white font-bold py-1 px-2 rounded text-sm"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">User Chat Management</h1>
        
        {/* Search and Filter Controls */}
        <div className="flex flex-col sm:flex-row gap-4 mb-4">
          <div className="flex-1">
            <input
              type="text"
              placeholder="Search chats or users..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="sm:w-64">
            <select
              value={filterUser}
              onChange={(e) => setFilterUser(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Users</option>
              {uniqueUsers.map(email => (
                <option key={email} value={email}>{email}</option>
              ))}
            </select>
          </div>
        </div>
        
        <p className="text-gray-600">
          Total: {filteredChats.length} chats
          {filterUser && ` for ${filterUser}`}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Chat List */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
              Chat Sessions
            </h3>
            
            <div className="max-h-96 overflow-y-auto">
              {filteredChats.length === 0 ? (
                <p className="text-gray-500 text-center py-4">No chats found</p>
              ) : (
                filteredChats.map((chat) => (
                  <div
                    key={chat.session_id}
                    onClick={() => handleChatSelect(chat)}
                    className={`p-3 border rounded-lg mb-2 cursor-pointer transition-colors ${
                      selectedChat?.session_id === chat.session_id
                        ? 'bg-blue-50 border-blue-500'
                        : 'bg-gray-50 border-gray-200 hover:bg-gray-100'
                    }`}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <h4 className="font-medium text-gray-900 truncate">{chat.title}</h4>
                      <span className="text-xs text-gray-500 ml-2 whitespace-nowrap">
                        {formatDate(chat.updated_at)}
                      </span>
                    </div>
                    
                    <div className="text-sm text-gray-600">
                      <p><strong>User:</strong> {chat.user_email}</p>
                      <p><strong>Created:</strong> {formatDate(chat.created_at)}</p>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Chat History */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
              Chat History
              {selectedChat && (
                <span className="text-sm font-normal text-gray-600 ml-2">
                  - {selectedChat.title}
                </span>
              )}
            </h3>
            
            {!selectedChat ? (
              <p className="text-gray-500 text-center py-8">
                Select a chat session to view its history
              </p>
            ) : historyLoading ? (
              <div className="flex justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
              </div>
            ) : (
              <div className="max-h-96 overflow-y-auto">
                {chatHistory.length === 0 ? (
                  <p className="text-gray-500 text-center py-4">No messages in this chat</p>
                ) : (
                  <div className="space-y-6">
                    {chatHistory.map((message) => (
                      <div key={message.id} className="border-b border-gray-200 pb-6">
                        {message.message_type === 'document_upload' ? (
                          <div className="bg-green-50 p-3 rounded-lg">
                            <div className="flex items-center text-green-800">
                              <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
                              </svg>
                              {message.query_text}
                            </div>
                            <p className="text-xs text-green-600 mt-1">
                              {formatDate(message.created_at)}
                            </p>
                          </div>
                        ) : (
                          <div className="space-y-3">
                            {/* 1. User Message */}
                            <div className="bg-blue-50 p-3 rounded-lg">
                              <p className="text-blue-800 font-medium text-sm mb-1">👤 User Message:</p>
                              <p className="text-blue-700">{message.query_text}</p>
                            </div>
                            
                            {/* 2. Prompt Sent to Gemini (Expandable) */}
                            {message.gemini_prompt && (
                              <AdminPromptSection 
                                title="🤖 Prompt Sent to Gemini API"
                                content={message.gemini_prompt}
                                bgColor="bg-purple-50"
                                textColor="text-purple-700"
                                headerColor="text-purple-800"
                              />
                            )}
                            
                            {/* 3. Raw Gemini Response (Expandable) */}
                            {message.gemini_raw_response && (
                              <AdminPromptSection 
                                title="⚡ Raw Gemini API Response"
                                content={message.gemini_raw_response}
                                bgColor="bg-orange-50"
                                textColor="text-orange-700"
                                headerColor="text-orange-800"
                              />
                            )}
                            
                            {/* 4. Final Assistant Response (Expandable) */}
                            {message.response_text && (
                              <AdminPromptSection 
                                title="✅ Final Assistant Response"
                                content={message.response_text}
                                bgColor="bg-gray-50"
                                textColor="text-gray-700"
                                headerColor="text-gray-800"
                              />
                            )}
                            
                            <p className="text-xs text-gray-500 mt-2">
                              {formatDate(message.created_at)}
                            </p>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminUserChatList;
