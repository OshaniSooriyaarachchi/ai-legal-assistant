import React, { useState, useEffect } from 'react';
import PromptTemplateEditor from './PromptTemplateEditor';
import PromptTemplateList from './PromptTemplateList';
import PromptVersionHistory from './PromptVersionHistory';
import { ApiService } from '../../services/api';

interface PromptTemplate {
  id?: string;
  name: string;
  title: string;
  description?: string;
  template_content?: string;
  placeholders?: string[];
  category: string;
  user_type: string;
  is_active: boolean;
  version?: number;
  created_at?: string;
  updated_at?: string;
  created_by?: string;
  modified_by?: string;
  variables?: string[];
}

interface Category {
  value: string;
  label: string;
}

interface UserType {
  value: string;
  label: string;
}

const AdminPromptManagement: React.FC = () => {
  const [selectedTemplate, setSelectedTemplate] = useState<PromptTemplate | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [showVersionHistory, setShowVersionHistory] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [categories, setCategories] = useState<Category[]>([]);
  const [userTypes, setUserTypes] = useState<UserType[]>([]);
  const [isLoadingData, setIsLoadingData] = useState(true);

  // Fetch categories and user types on component mount
  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoadingData(true);
        
        // Fetch categories
        const categoriesResponse = await ApiService.getPromptCategories();
        const fetchedCategories = categoriesResponse.categories || [];
        setCategories(fetchedCategories.map((cat: string) => ({ 
          value: cat, 
          label: cat.charAt(0).toUpperCase() + cat.slice(1) 
        })));

        // Fetch user types
        const userTypesResponse = await ApiService.getPromptUserTypes();
        const fetchedUserTypes = userTypesResponse.user_types || [];
        setUserTypes(fetchedUserTypes.map((type: string) => ({ 
          value: type, 
          label: type.charAt(0).toUpperCase() + type.slice(1) 
        })));

      } catch (error) {
        console.error('Error fetching categories and user types:', error);
        // Set default values if API fails
        setCategories([
          { value: 'system', label: 'System' },
          { value: 'legal', label: 'Legal' },
          { value: 'general', label: 'General' },
          { value: 'admin', label: 'Admin' }
        ]);
        setUserTypes([
          { value: 'all', label: 'All' },
          { value: 'admin', label: 'Admin' },
          { value: 'premium', label: 'Premium' },
          { value: 'basic', label: 'Basic' }
        ]);
      } finally {
        setIsLoadingData(false);
      }
    };

    fetchData();
  }, []);

  const handleSelectTemplate = (template: PromptTemplate) => {
    setSelectedTemplate(template);
    setIsCreating(false);
  };

  const handleCreateNew = () => {
    setSelectedTemplate(null);
    setIsCreating(true);
  };

  const handleSaveTemplate = () => {
    setSelectedTemplate(null);
    setIsCreating(false);
    // Trigger refresh of the template list
    setRefreshTrigger(prev => prev + 1);
  };

  const handleCancel = () => {
    setSelectedTemplate(null);
    setIsCreating(false);
  };

  const handleShowVersionHistory = () => {
    if (selectedTemplate) {
      setShowVersionHistory(true);
    }
  };

  const handleCloseVersionHistory = () => {
    setShowVersionHistory(false);
  };

  const handleVersionRestore = () => {
    // Refresh the current template and list
    setRefreshTrigger(prev => prev + 1);
    setShowVersionHistory(false);
  };

  if (isLoadingData) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div className="spinner-border text-blue-600 mb-4" role="status">
            <span className="sr-only">Loading...</span>
          </div>
          <p className="text-gray-600">Loading prompt management data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Prompt Template Management</h1>
        <p className="text-gray-600">
          Create, edit, and manage prompt templates for the AI legal assistant. 
          Organize templates by category and track version history.
        </p>
      </div>

      <div className="flex-1 flex gap-6 min-h-0">
        {/* Left Panel - Template List */}
        <div className="w-1/2 flex flex-col">
          <PromptTemplateList
            key={refreshTrigger} // Force refresh when needed
            onSelectTemplate={handleSelectTemplate}
            onCreateNew={handleCreateNew}
            selectedTemplateId={selectedTemplate?.id}
          />
        </div>

        {/* Right Panel - Template Editor */}
        <div className="w-1/2 flex flex-col">
          {(selectedTemplate || isCreating) ? (
            <div className="bg-white rounded-lg shadow flex flex-col h-full">
              <div className="p-4 border-b border-gray-200 flex justify-between items-center">
                <h2 className="text-xl font-semibold text-gray-900">
                  {isCreating ? 'Create New Template' : `Edit Template: ${selectedTemplate?.name}`}
                </h2>
                <div className="flex gap-2">
                  {selectedTemplate && !isCreating && (
                    <button
                      onClick={handleShowVersionHistory}
                      className="px-3 py-1 text-sm text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded transition-colors"
                    >
                      Version History
                    </button>
                  )}
                  <button
                    onClick={handleCancel}
                    className="text-gray-400 hover:text-gray-600 text-xl font-bold"
                  >
                    ×
                  </button>
                </div>
              </div>
              <div className="flex-1 overflow-hidden">
                <PromptTemplateEditor
                  prompt={selectedTemplate}
                  categories={categories}
                  userTypes={userTypes}
                  isCreating={isCreating}
                  onSave={handleSaveTemplate}
                  onCancel={handleCancel}
                />
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow flex items-center justify-center h-full">
              <div className="text-center text-gray-500">
                <div className="mb-4">
                  <svg 
                    className="mx-auto h-16 w-16 text-gray-300" 
                    fill="none" 
                    viewBox="0 0 24 24" 
                    stroke="currentColor"
                  >
                    <path 
                      strokeLinecap="round" 
                      strokeLinejoin="round" 
                      strokeWidth={1} 
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" 
                    />
                  </svg>
                </div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  No template selected
                </h3>
                <p className="text-sm text-gray-500 mb-4">
                  Choose a template from the list to edit, or create a new one to get started.
                </p>
                <button
                  onClick={handleCreateNew}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Create New Template
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Version History Modal */}
      {showVersionHistory && selectedTemplate && selectedTemplate.id && (
        <PromptVersionHistory
          templateId={selectedTemplate.id}
          onClose={handleCloseVersionHistory}
          onRestore={handleVersionRestore}
        />
      )}
    </div>
  );
};

export default AdminPromptManagement;
