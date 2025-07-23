import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '../app/hooks';
import { signOut } from '../features/auth/authSlice';
import ChatInterface from './ChatInterface';
import ChatSessionList from './ChatSessionList';
import { loadChatSessions } from '../features/chat/chatSlice';
import { checkAdminRole } from '../utils/authUtils';
import { supabase } from '../lib/supabase';

const Dashboard: React.FC = () => {
  const dispatch = useAppDispatch();
  const { user } = useAppSelector((state) => state.auth);
  const navigate = useNavigate();
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    // Load chat sessions when dashboard mounts
    dispatch(loadChatSessions());
  }, [dispatch]);

  useEffect(() => {
    checkAdminStatus();
  }, []);

  const checkAdminStatus = async () => {
    const adminStatus = await checkAdminRole(supabase);
    setIsAdmin(adminStatus);
  };

  const handleSignOut = async () => {
    await dispatch(signOut());
    navigate('/login');
  };

  // Also add this to see the current state
  console.log('Current isAdmin state:', isAdmin);

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      <nav className="bg-white shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center h-16">
          <div className="flex items-center pl-4">
            <h1 className="text-xl font-bold text-indigo-600">AI Legal Assistant</h1>
          </div>
          <div className="flex-1"></div>
          <div className="flex items-center space-x-4 pr-4">
            <span className="text-gray-700">Welcome, {user?.email}</span>
            {isAdmin && (
              <Link
                to="/admin"
                className="bg-purple-600 text-white px-4 py-2 rounded-md hover:bg-purple-700"
              >
                Admin Panel
              </Link>
            )}
            <button
              onClick={handleSignOut}
              className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700"
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