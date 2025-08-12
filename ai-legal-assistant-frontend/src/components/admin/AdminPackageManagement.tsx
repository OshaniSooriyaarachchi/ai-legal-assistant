import React, { useState, useEffect } from 'react';
import { ApiService, AdminPackage, PackageFormData } from '../../services/api';
import PackageForm from './PackageForm';
import PackageList from './PackageList';

const AdminPackageManagement: React.FC = () => {
  const [packages, setPackages] = useState<AdminPackage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingPackage, setEditingPackage] = useState<AdminPackage | null>(null);
  const [activeTab, setActiveTab] = useState<'list' | 'create' | 'assign'>('list');
  const [deletingPackageId, setDeletingPackageId] = useState<string | null>(null);

  useEffect(() => {
    loadPackages();
  }, []);

  const loadPackages = async () => {
    try {
      setLoading(true);
      const response = await ApiService.getAdminPackages();
      setPackages(response.packages || []);
      setError(null);
    } catch (err) {
      setError('Failed to load packages');
      console.error('Error loading packages:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreatePackage = async (formData: PackageFormData) => {
    try {
      await ApiService.createPackage(formData);
      await loadPackages();
      setShowCreateForm(false);
      setActiveTab('list');
    } catch (err) {
      throw new Error('Failed to create package');
    }
  };

  const handleUpdatePackage = async (packageId: string, formData: PackageFormData) => {
    try {
      await ApiService.updatePackage(packageId, formData);
      await loadPackages();
      setEditingPackage(null);
    } catch (err) {
      throw new Error('Failed to update package');
    }
  };

  const handleDeletePackage = async (packageId: string) => {
    setDeletingPackageId(packageId);
  };

  const confirmDeletePackage = async () => {
    if (!deletingPackageId) return;

    try {
      await ApiService.deletePackage(deletingPackageId);
      await loadPackages();
      setDeletingPackageId(null);
    } catch (err) {
      setError('Failed to delete package');
      console.error('Error deleting package:', err);
      setDeletingPackageId(null);
    }
  };

  const cancelDeletePackage = () => {
    setDeletingPackageId(null);
  };

  const tabs = [
    { id: 'list' as const, label: 'Manage Packages', icon: '⚙️' },
    { id: 'create' as const, label: 'Create Package', icon: '➕' },
    { id: 'assign' as const, label: 'Assign Packages', icon: '👥' },
  ];

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Package Management</h1>
        <p className="text-gray-600 mt-2">Create and manage subscription packages</p>
      </div>

      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
          <button
            onClick={() => setError(null)}
            className="float-right text-red-500 hover:text-red-700"
          >
            ×
          </button>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="border-b border-gray-200 mb-8">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`py-2 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <span className="mr-2">{tab.icon}</span>
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Content */}
      <div>
        {activeTab === 'list' && (
          <PackageList
            packages={packages}
            loading={loading}
            onEdit={setEditingPackage}
            onDelete={handleDeletePackage}
            onRefresh={loadPackages}
          />
        )}

        {activeTab === 'create' && (
          <PackageForm
            package={editingPackage}
            onSubmit={editingPackage 
              ? (data: PackageFormData) => handleUpdatePackage(editingPackage.id, data)
              : handleCreatePackage
            }
            onCancel={() => {
              setEditingPackage(null);
              setActiveTab('list');
            }}
          />
        )}

        {activeTab === 'assign' && (
          <div className="bg-white shadow rounded-lg p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              Assign Packages to Users
            </h3>
            <p className="text-gray-600">
              Package assignment functionality coming soon...
            </p>
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {deletingPackageId && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div className="mt-3 text-center">
              <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100">
                <span className="text-2xl">⚠️</span>
              </div>
              <h3 className="text-lg font-medium text-gray-900 mt-4">Delete Package</h3>
              <div className="mt-2 px-7 py-3">
                <p className="text-sm text-gray-500">
                  Are you sure you want to delete this package? This action cannot be undone.
                </p>
              </div>
              <div className="flex justify-center space-x-4 mt-4">
                <button
                  onClick={cancelDeletePackage}
                  className="px-4 py-2 bg-gray-300 text-gray-700 text-base font-medium rounded-md shadow-sm hover:bg-gray-400"
                >
                  Cancel
                </button>
                <button
                  onClick={confirmDeletePackage}
                  className="px-4 py-2 bg-red-600 text-white text-base font-medium rounded-md shadow-sm hover:bg-red-700"
                >
                  Delete
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminPackageManagement;
