import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../../lib/supabase';
import DocumentUploadAdmin from './DocumentUploadAdmin';
import AdminDocumentList from './AdminDocumentList';
import AdminStatistics from './AdminStatistics';
import AdminUserChatList from './AdminUserChatList';
import AdminUserDocuments from './AdminUserDocuments';
import AdminPackageManagement from './AdminPackageManagement';
import AdminPromptManagement from './AdminPromptManagement';

interface TabType {
  id: string;
  label: string;
  component: React.ComponentType;
}

const AdminDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState('upload');
  const [isAdmin, setIsAdmin] = useState(false);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    checkAdminStatus();
  }, []);

  const checkAdminStatus = async () => {
    try {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) {
        setLoading(false);
        return;
      }

      const { data } = await supabase
        .from('user_roles')
        .select('role')
        .eq('user_id', user.id)
        .eq('role', 'admin')
        .eq('is_active', true);

      setIsAdmin(Boolean(data && data.length > 0));
    } catch (error) {
      console.error('Error checking admin status:', error);
    } finally {
      setLoading(false);
    }
  };

  const tabs: TabType[] = [
    { id: 'upload', label: 'Upload Documents', component: DocumentUploadAdmin },
    { id: 'manage', label: 'Manage Documents', component: AdminDocumentList },
    { id: 'prompts', label: 'Manage Prompts', component: AdminPromptManagement },
    { id: 'packages', label: 'Manage Packages', component: AdminPackageManagement },
    { id: 'user-chats', label: 'User Chats', component: AdminUserChatList },
    { id: 'user-documents', label: 'User Documents', component: AdminUserDocuments },
    { id: 'statistics', label: 'Statistics', component: AdminStatistics },
  ];

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!isAdmin) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Access Denied</h2>
        <p className="text-gray-600">You don't have admin privileges to access this page.</p>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col">
      {/* Fixed Header Section */}
      <div className="flex-shrink-0 bg-white border-b border-gray-200 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="py-8 flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Admin Dashboard</h1>
              <p className="text-gray-600 mt-2">Manage the legal knowledge base</p>
            </div>
            <button
              onClick={() => navigate('/dashboard')}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              ← Back to Chat
            </button>
          </div>

          {/* Fixed Tab Navigation */}
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`py-2 px-1 border-b-2 font-medium text-sm ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>
        </div>
      </div>

      {/* Scrollable Content Area */}
      <div className="flex-1 overflow-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Tab Content */}
          {tabs.map((tab) => (
            activeTab === tab.id && <tab.component key={tab.id} />
          ))}
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;