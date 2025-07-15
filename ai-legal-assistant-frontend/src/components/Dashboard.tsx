import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '../app/hooks';
import { signOut } from '../features/auth/authSlice';
import ChatInterface from './ChatInterface';
import ChatSessionList from './ChatSessionList';
import { loadChatSessions } from '../features/chat/chatSlice';

const Dashboard: React.FC = () => {
  const dispatch = useAppDispatch();
  const { user } = useAppSelector((state) => state.auth);
  const navigate = useNavigate();

  useEffect(() => {
    // Load chat sessions when dashboard mounts
    dispatch(loadChatSessions());
  }, [dispatch]);

  const handleSignOut = async () => {
    await dispatch(signOut());
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <h1 className="text-xl font-bold text-indigo-600">AI Legal Assistant</h1>
              </div>
            </div>
            <div className="flex items-center">
              <span className="text-gray-700 mr-4">Welcome, {user?.email}</span>
              <button
                onClick={handleSignOut}
                className="ml-4 px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700"
              >
                Sign out
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content Area with Sidebar */}
      <div className="flex-1 flex">
        {/* Chat Sessions Sidebar */}
        <ChatSessionList />
        
        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col">
          <div className="flex-1">
            <ChatInterface />
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;