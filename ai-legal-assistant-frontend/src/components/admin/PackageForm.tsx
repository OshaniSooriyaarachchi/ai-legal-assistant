import React, { useState, useEffect } from 'react';
import { PackageFormData, AdminPackage } from '../../services/api';

interface PackageFormProps {
  package?: AdminPackage | null;
  onSubmit: (data: PackageFormData) => Promise<void>;
  onCancel: () => void;
}

const PackageForm: React.FC<PackageFormProps> = ({ package: editPackage, onSubmit, onCancel }) => {
  const [formData, setFormData] = useState<PackageFormData>({
    name: '',
    display_name: '',
    daily_query_limit: 10,
    max_document_size_mb: 5,
    max_documents_per_user: 10,
    price_monthly: 0,
    features: [],
    is_active: true,
  });

  const [newFeature, setNewFeature] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (editPackage) {
      setFormData({
        name: editPackage.name,
        display_name: editPackage.display_name,
        daily_query_limit: editPackage.daily_query_limit,
        max_document_size_mb: editPackage.max_document_size_mb,
        max_documents_per_user: editPackage.max_documents_per_user,
        price_monthly: editPackage.price_monthly,
        features: [...editPackage.features],
        is_active: editPackage.is_active,
      });
    }
  }, [editPackage]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await onSubmit(formData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (field: keyof PackageFormData, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const addFeature = () => {
    if (newFeature.trim() && !formData.features.includes(newFeature.trim())) {
      handleInputChange('features', [...formData.features, newFeature.trim()]);
      setNewFeature('');
    }
  };

  const removeFeature = (index: number) => {
    const updatedFeatures = formData.features.filter((_, i) => i !== index);
    handleInputChange('features', updatedFeatures);
  };

  return (
    <div className="bg-white shadow rounded-lg">
      <div className="px-6 py-4 border-b border-gray-200">
        <h3 className="text-lg font-medium text-gray-900">
          {editPackage ? 'Edit Package' : 'Create New Package'}
        </h3>
      </div>

      <form onSubmit={handleSubmit} className="p-6 space-y-6">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Package Name */}
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-gray-700">
              Package Name (Internal)
            </label>
            <input
              type="text"
              id="name"
              value={formData.name}
              onChange={(e) => handleInputChange('name', e.target.value)}
              className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              placeholder="e.g., premium_pro"
              required
            />
          </div>

          {/* Display Name */}
          <div>
            <label htmlFor="display_name" className="block text-sm font-medium text-gray-700">
              Display Name
            </label>
            <input
              type="text"
              id="display_name"
              value={formData.display_name}
              onChange={(e) => handleInputChange('display_name', e.target.value)}
              className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              placeholder="e.g., Premium Pro Plan"
              required
            />
          </div>

          {/* Daily Query Limit */}
          <div>
            <label htmlFor="daily_query_limit" className="block text-sm font-medium text-gray-700">
              Daily Query Limit (-1 for unlimited)
            </label>
            <input
              type="number"
              id="daily_query_limit"
              value={formData.daily_query_limit}
              onChange={(e) => handleInputChange('daily_query_limit', parseInt(e.target.value))}
              className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              required
            />
          </div>

          {/* Max Document Size */}
          <div>
            <label htmlFor="max_document_size_mb" className="block text-sm font-medium text-gray-700">
              Max Document Size (MB)
            </label>
            <input
              type="number"
              id="max_document_size_mb"
              value={formData.max_document_size_mb}
              onChange={(e) => handleInputChange('max_document_size_mb', parseInt(e.target.value))}
              className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              required
            />
          </div>

          {/* Max Documents Per User */}
          <div>
            <label htmlFor="max_documents_per_user" className="block text-sm font-medium text-gray-700">
              Max Documents Per User
            </label>
            <input
              type="number"
              id="max_documents_per_user"
              value={formData.max_documents_per_user}
              onChange={(e) => handleInputChange('max_documents_per_user', parseInt(e.target.value))}
              className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              required
            />
          </div>

          {/* Monthly Price */}
          <div>
            <label htmlFor="price_monthly" className="block text-sm font-medium text-gray-700">
              Monthly Price ($)
            </label>
            <input
              type="number"
              step="0.01"
              id="price_monthly"
              value={formData.price_monthly}
              onChange={(e) => handleInputChange('price_monthly', parseFloat(e.target.value))}
              className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              required
            />
          </div>
        </div>

        {/* Features */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Features
          </label>
          
          {/* Add Feature */}
          <div className="flex mb-3">
            <input
              type="text"
              value={newFeature}
              onChange={(e) => setNewFeature(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addFeature())}
              className="flex-1 border border-gray-300 rounded-l-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              placeholder="Add a feature..."
            />
            <button
              type="button"
              onClick={addFeature}
              className="px-4 py-2 bg-blue-600 text-white rounded-r-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              Add
            </button>
          </div>

          {/* Feature List */}
          {formData.features.length > 0 && (
            <div className="space-y-2">
              {formData.features.map((feature, index) => (
                <div key={index} className="flex items-center justify-between bg-gray-50 px-3 py-2 rounded">
                  <span className="text-sm text-gray-900">{feature}</span>
                  <button
                    type="button"
                    onClick={() => removeFeature(index)}
                    className="text-red-600 hover:text-red-800 text-sm"
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Active Status */}
        <div className="flex items-center">
          <input
            type="checkbox"
            id="is_active"
            checked={formData.is_active}
            onChange={(e) => handleInputChange('is_active', e.target.checked)}
            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
          />
          <label htmlFor="is_active" className="ml-2 block text-sm text-gray-900">
            Package is active
          </label>
        </div>

        {/* Form Actions */}
        <div className="flex justify-end space-x-3 pt-6 border-t border-gray-200">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={loading}
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          >
            {loading ? 'Saving...' : editPackage ? 'Update Package' : 'Create Package'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default PackageForm;
