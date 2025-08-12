import React from 'react';
import { AdminPackage } from '../../services/api';

interface PackageListProps {
  packages: AdminPackage[];
  loading: boolean;
  onEdit: (pkg: AdminPackage) => void;
  onDelete: (id: string) => void;
  onRefresh: () => void;
}

const PackageList: React.FC<PackageListProps> = ({ packages, onEdit, onDelete, onRefresh }) => {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const getQueryLimitText = (limit: number) => {
    return limit === -1 ? 'Unlimited' : `${limit} per day`;
  };

  return (
    <div className="bg-white shadow rounded-lg">
      <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
        <h3 className="text-lg font-medium text-gray-900">Subscription Packages</h3>
        <button
          onClick={onRefresh}
          className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Refresh
        </button>
      </div>

      {packages.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-500">No packages found. Create your first package!</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Package Details
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Limits
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Price
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Subscriptions
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {packages.map((pkg) => (
                <tr key={pkg.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div>
                      <div className="text-sm font-medium text-gray-900">
                        {pkg.display_name}
                      </div>
                      <div className="text-sm text-gray-500">
                        {pkg.name}
                        {pkg.is_custom && (
                          <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                            Custom
                          </span>
                        )}
                      </div>
                      {pkg.features && pkg.features.length > 0 && (
                        <div className="mt-1">
                          <div className="text-xs text-gray-400">Features:</div>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {pkg.features.slice(0, 2).map((feature, index) => (
                              <span
                                key={index}
                                className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800"
                              >
                                {feature}
                              </span>
                            ))}
                            {pkg.features.length > 2 && (
                              <span className="text-xs text-gray-500">
                                +{pkg.features.length - 2} more
                              </span>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    <div className="space-y-1">
                      <div>Queries: {getQueryLimitText(pkg.daily_query_limit)}</div>
                      <div>Docs: {pkg.max_documents_per_user}</div>
                      <div>Size: {pkg.max_document_size_mb}MB</div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    <div className="font-medium">
                      {formatCurrency(pkg.price_monthly)}/month
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        pkg.is_active
                          ? 'bg-green-100 text-green-800'
                          : 'bg-red-100 text-red-800'
                      }`}
                    >
                      {pkg.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    <div className="flex items-center">
                      <span className="text-gray-400 mr-1">👥</span>
                      {pkg.active_subscriptions || 0}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <div className="flex space-x-2">
                      <button
                        onClick={() => onEdit(pkg)}
                        className="text-blue-600 hover:text-blue-900 flex items-center px-2 py-1 border border-blue-300 rounded text-xs"
                        title="Edit package"
                      >
                        ✏️ Edit
                      </button>
                      {pkg.is_custom && (pkg.active_subscriptions || 0) === 0 && (
                        <button
                          onClick={() => onDelete(pkg.id)}
                          className="text-red-600 hover:text-red-900 flex items-center px-2 py-1 border border-red-300 rounded text-xs"
                          title="Delete package"
                        >
                          🗑️ Delete
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default PackageList;
