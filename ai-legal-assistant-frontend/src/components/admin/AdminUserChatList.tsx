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
  message_type: string;
  created_at: string;
  document_ids?: string[];
}

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
    return new Date(dateString).toLocaleString();
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
                  <div className="space-y-4">
                    {chatHistory.map((message) => (
                      <div key={message.id} className="border-b border-gray-200 pb-4">
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
                          <>
                            <div className="bg-blue-50 p-3 rounded-lg mb-2">
                              <p className="text-blue-800 font-medium">User:</p>
                              <p className="text-blue-700">{message.query_text}</p>
                            </div>
                            
                            {message.response_text && (
                              <div className="bg-gray-50 p-3 rounded-lg">
                                <p className="text-gray-800 font-medium">Assistant:</p>
                                <p className="text-gray-700 whitespace-pre-wrap">
                                  {formatMessage(message.response_text, 300)}
                                </p>
                              </div>
                            )}
                            
                            <p className="text-xs text-gray-500 mt-2">
                              {formatDate(message.created_at)}
                            </p>
                          </>
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
