import React, { useEffect, useState } from 'react';
import { useAppDispatch, useAppSelector } from '../app/hooks';
import { createChatSession, loadChatSessions, loadChatHistory, setCurrentSession, clearChatLocal, deleteChatSession } from '../features/chat/chatSlice';

interface ChatSessionListProps {
  onSessionSelect?: (sessionId: string) => void;
}

export const ChatSessionList: React.FC<ChatSessionListProps> = ({ onSessionSelect }) => {
  const dispatch = useAppDispatch();
  const { sessions, currentSessionId, loading } = useAppSelector(state => state.chat);
  const [deletingSessionId, setDeletingSessionId] = useState<string | null>(null);

  useEffect(() => {
    dispatch(loadChatSessions());
  }, [dispatch]);

  const handleNewChat = async () => {
    try {
      const result = await dispatch(createChatSession()).unwrap();
      dispatch(setCurrentSession(result.id));
      onSessionSelect?.(result.id);
    } catch (error) {
      console.error('Failed to create new chat session:', error);
    }
  };

  const handleSessionClick = async (sessionId: string) => {
    try {
      dispatch(setCurrentSession(sessionId));
      await dispatch(loadChatHistory(sessionId));
      onSessionSelect?.(sessionId);
    } catch (error) {
      console.error('Failed to load chat history:', error);
    }
  };

  const handleDeleteSession = async (sessionId: string, event: React.MouseEvent) => {
    event.stopPropagation(); // Prevent session selection when clicking delete
    
    if (window.confirm('Are you sure you want to delete this chat session? This action cannot be undone.')) {
      try {
        setDeletingSessionId(sessionId);
        await dispatch(deleteChatSession(sessionId)).unwrap();
      } catch (error) {
        console.error('Failed to delete chat session:', error);
        alert('Failed to delete chat session. Please try again.');
      } finally {
        setDeletingSessionId(null);
      }
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - date.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 1) {
      return 'Today';
    } else if (diffDays === 2) {
      return 'Yesterday';
    } else if (diffDays <= 7) {
      return `${diffDays - 1} days ago`;
    } else {
      return date.toLocaleDateString();
    }
  };

  return (
    <div className="w-80 bg-white border-r border-gray-300 flex flex-col h-full">
      {/* Header with New Chat button */}
      <div className="p-4 border-b border-gray-200 bg-gray-50">
        <button
          onClick={handleNewChat}
          disabled={loading}
          className="w-full bg-blue-600 text-white px-4 py-3 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          <span className="text-lg">+</span>
          New Chat
        </button>
      </div>
      
      {/* Chat Sessions List */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-3">
          <h3 className="text-sm font-semibold text-gray-600 mb-3 px-2">Recent Chats</h3>
          
          {sessions.length === 0 ? (
            <div className="text-center py-8">
              <div className="text-gray-400 mb-2">
                <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
              </div>
              <p className="text-sm text-gray-500">No previous chats</p>
              <p className="text-xs text-gray-400 mt-1">Start a new conversation to begin</p>
            </div>
          ) : (
            <div className="space-y-1">
              {sessions
                .filter(session => session && session.id) // Filter out invalid sessions
                .map((session) => (
                <div
                  key={session.id}
                  onClick={() => handleSessionClick(session.id)}
                  className={`w-full text-left p-3 rounded-lg text-sm transition-all duration-200 group hover:bg-gray-50 cursor-pointer ${
                    currentSessionId === session.id
                      ? 'bg-blue-50 border border-blue-200 text-blue-900'
                      : 'hover:bg-gray-50 text-gray-700 border border-transparent'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="truncate font-medium">
                        {session.title || (session.id ? `Chat ${session.id.slice(0, 8)}...` : 'New Chat')}
                      </div>
                      <div className={`text-xs mt-1 ${
                        currentSessionId === session.id ? 'text-blue-600' : 'text-gray-500'
                      }`}>
                        {session.created_at ? formatDate(session.created_at) : 'Just now'}
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2 ml-2">
                      {currentSessionId === session.id && (
                        <div className="flex-shrink-0">
                          <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                        </div>
                      )}
                      
                      {/* Delete Button */}
                      <button
                        onClick={(e) => handleDeleteSession(session.id, e)}
                        disabled={deletingSessionId === session.id}
                        className={`opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-red-100 text-gray-400 hover:text-red-600 ${
                          deletingSessionId === session.id ? 'opacity-100' : ''
                        }`}
                        title="Delete chat session"
                      >
                        {deletingSessionId === session.id ? (
                          <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                          </svg>
                        ) : (
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      
      {/* Footer */}
      <div className="p-3 border-t border-gray-200 bg-gray-50">
        <div className="text-xs text-gray-500 text-center">
          {sessions.length} chat{sessions.length !== 1 ? 's' : ''} total
        </div>
      </div>
    </div>
  );
};

export default ChatSessionList;
