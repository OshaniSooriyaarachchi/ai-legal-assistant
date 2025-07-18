import React, { useState, useEffect } from 'react';
import { supabase } from '../../lib/supabase';
import DocumentUploadAdmin from './DocumentUploadAdmin';
import AdminDocumentList from './AdminDocumentList';
import AdminStatistics from './AdminStatistics';

interface TabType {
  id: string;
  label: string;
  component: React.ComponentType;
}

const AdminDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState('upload');
  const [isAdmin, setIsAdmin] = useState(false);
  const [loading, setLoading] = useState(true);

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
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Admin Dashboard</h1>
        <p className="text-gray-600 mt-2">Manage the legal knowledge base</p>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200 mb-8">
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

      {/* Tab Content */}
      <div>
        {tabs.map((tab) => (
          activeTab === tab.id && <tab.component key={tab.id} />
        ))}
      </div>
    </div>
  );
};

export default AdminDashboard;