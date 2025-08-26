import React, { useState, useEffect } from 'react';
import { ApiService } from '../../services/api';

interface PromptVersion {
  id: string;
  template_id: string;
  version_number: number;
  template_content: string;
  variables: string[];
  description: string;
  created_at: string;
  created_by: string;
  is_current: boolean;
}

interface PromptVersionHistoryProps {
  templateId: string;
  onClose: () => void;
  onRestore?: (versionNumber: number) => void;
}

interface ConfirmDialogProps {
  isOpen: boolean;
  title: string;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
}

const ConfirmDialog: React.FC<ConfirmDialogProps> = ({ isOpen, title, message, onConfirm, onCancel }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
        <p className="text-gray-600 mb-6">{message}</p>
        <div className="flex justify-end space-x-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Restore
          </button>
        </div>
      </div>
    </div>
  );
};

const PromptVersionHistory: React.FC<PromptVersionHistoryProps> = ({ 
  templateId, 
  onClose, 
  onRestore 
}) => {
  const [versions, setVersions] = useState<PromptVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedVersion, setSelectedVersion] = useState<PromptVersion | null>(null);
  const [showRestoreConfirm, setShowRestoreConfirm] = useState(false);
  const [versionToRestore, setVersionToRestore] = useState<number | null>(null);

  useEffect(() => {
    loadVersionHistory();
  }, [templateId]);

  const loadVersionHistory = async () => {
    try {
      setLoading(true);
      const response = await ApiService.getPromptVersionHistory(templateId);
      setVersions(response.data || []);
    } catch (error) {
      console.error('Error loading version history:', error);
      alert('Failed to load version history');
    } finally {
      setLoading(false);
    }
  };

  const handleRestore = async (versionNumber: number) => {
    setVersionToRestore(versionNumber);
    setShowRestoreConfirm(true);
  };

  const confirmRestore = async () => {
    if (!versionToRestore) return;

    try {
      await ApiService.restorePromptVersion(templateId, versionToRestore);
      alert(`Version ${versionToRestore} restored successfully`);
      if (onRestore) {
        onRestore(versionToRestore);
      }
      loadVersionHistory();
    } catch (error) {
      console.error('Error restoring version:', error);
      alert('Failed to restore version');
    } finally {
      setShowRestoreConfirm(false);
      setVersionToRestore(null);
    }
  };

  const cancelRestore = () => {
    setShowRestoreConfirm(false);
    setVersionToRestore(null);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const truncateContent = (content: string, maxLength: number = 200) => {
    if (content.length <= maxLength) return content;
    return content.substring(0, maxLength) + '...';
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-6 max-w-4xl w-full mx-4 max-h-screen overflow-hidden">
          <div className="flex items-center justify-center h-48">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-6xl w-full mx-4 max-h-screen flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-gray-200 flex justify-between items-center">
          <h2 className="text-xl font-semibold text-gray-900">
            Version History ({versions.length} versions)
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl font-bold"
          >
            ×
          </button>
        </div>

        <div className="flex flex-1 overflow-hidden">
          {/* Version List */}
          <div className="w-1/3 border-r border-gray-200 overflow-y-auto">
            <div className="p-4">
              <h3 className="text-sm font-medium text-gray-700 mb-3">Select Version</h3>
              <div className="space-y-2">
                {versions.map((version) => (
                  <div
                    key={version.id}
                    className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                      selectedVersion?.id === version.id
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                    }`}
                    onClick={() => setSelectedVersion(version)}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium text-sm">
                        Version {version.version_number}
                        {version.is_current && (
                          <span className="ml-2 px-2 py-1 text-xs bg-green-100 text-green-800 rounded-full">
                            Current
                          </span>
                        )}
                      </span>
                    </div>
                    <div className="text-xs text-gray-500">
                      <div>By: {version.created_by}</div>
                      <div>{formatDate(version.created_at)}</div>
                    </div>
                    {version.description && (
                      <div className="text-xs text-gray-600 mt-1">
                        {truncateContent(version.description, 80)}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Version Details */}
          <div className="flex-1 overflow-y-auto">
            {selectedVersion ? (
              <div className="p-6">
                <div className="mb-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-medium text-gray-900">
                      Version {selectedVersion.version_number} Details
                    </h3>
                    {!selectedVersion.is_current && onRestore && (
                      <button
                        onClick={() => handleRestore(selectedVersion.version_number)}
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                      >
                        Restore This Version
                      </button>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-4 mb-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Created By
                      </label>
                      <p className="text-sm text-gray-900">{selectedVersion.created_by}</p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Created At
                      </label>
                      <p className="text-sm text-gray-900">{formatDate(selectedVersion.created_at)}</p>
                    </div>
                  </div>

                  {selectedVersion.description && (
                    <div className="mb-6">
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Description
                      </label>
                      <p className="text-sm text-gray-900 bg-gray-50 p-3 rounded-lg">
                        {selectedVersion.description}
                      </p>
                    </div>
                  )}

                  {selectedVersion.variables.length > 0 && (
                    <div className="mb-6">
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Variables ({selectedVersion.variables.length})
                      </label>
                      <div className="flex flex-wrap gap-2">
                        {selectedVersion.variables.map((variable, index) => (
                          <span
                            key={index}
                            className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full"
                          >
                            {variable}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Template Content
                    </label>
                    <div className="bg-gray-50 rounded-lg p-4 max-h-96 overflow-y-auto">
                      <pre className="text-sm text-gray-900 whitespace-pre-wrap font-mono">
                        {selectedVersion.template_content}
                      </pre>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-500">
                <div className="text-center">
                  <p className="text-lg font-medium mb-2">Select a version to view details</p>
                  <p className="text-sm">Choose a version from the list on the left to see its content and restore it if needed.</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
      
      <ConfirmDialog
        isOpen={showRestoreConfirm}
        title="Restore Version"
        message={`Are you sure you want to restore version ${versionToRestore}? This will create a new version with the content from version ${versionToRestore}.`}
        onConfirm={confirmRestore}
        onCancel={cancelRestore}
      />
    </div>
  );
};

export default PromptVersionHistory;
