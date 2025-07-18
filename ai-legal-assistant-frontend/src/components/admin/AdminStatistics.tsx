import React, { useState, useEffect } from 'react';
import { ApiService } from '../../services/api';

interface Statistics {
  public_documents: number;
  total_documents: number;
  active_users: number;
  recent_uploads: any[];
}

const AdminStatistics: React.FC = () => {
  const [stats, setStats] = useState<Statistics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStatistics();
  }, []);

  const fetchStatistics = async () => {
    try {
      const response = await ApiService.getAdminStatistics();
      setStats(response.statistics);
    } catch (error) {
      console.error('Error fetching statistics:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Failed to load statistics</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-medium text-gray-900">System Statistics</h3>
      
      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="text-2xl font-bold text-blue-600">{stats.public_documents}</div>
          <div className="text-sm text-gray-600">Public Documents</div>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="text-2xl font-bold text-green-600">{stats.total_documents}</div>
          <div className="text-sm text-gray-600">Total Documents</div>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="text-2xl font-bold text-purple-600">{stats.active_users}</div>
          <div className="text-sm text-gray-600">Active Users</div>
        </div>
      </div>

      {/* Recent Uploads */}
      {stats.recent_uploads.length > 0 && (
        <div className="bg-white p-6 rounded-lg shadow">
          <h4 className="text-md font-medium text-gray-900 mb-4">Recent Uploads</h4>
          <div className="space-y-3">
            {stats.recent_uploads.map((upload, index) => (
              <div key={index} className="flex justify-between items-center">
                <div>
                  <div className="text-sm font-medium text-gray-900">{upload.title}</div>
                  <div className="text-xs text-gray-500">
                    {upload.document_category?.replace('_', ' ') || 'Uncategorized'}
                  </div>
                </div>
                <div className="text-xs text-gray-500">
                  {new Date(upload.created_at).toLocaleDateString()}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminStatistics;