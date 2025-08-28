import React, { useState, useEffect } from 'react';
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
            className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
};

interface PromptTemplateListProps {
  onSelectTemplate: (template: PromptTemplate) => void;
  onCreateNew: () => void;
  selectedTemplateId?: string;
}

const PromptTemplateList: React.FC<PromptTemplateListProps> = ({ 
  onSelectTemplate, 
  onCreateNew, 
  selectedTemplateId 
}) => {
  const [templates, setTemplates] = useState<PromptTemplate[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [showInactiveTemplates, setShowInactiveTemplates] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [templateToDelete, setTemplateToDelete] = useState<string | null>(null);

  useEffect(() => {
    loadTemplates();
    loadCategories();
  }, []);

  const loadTemplates = async () => {
    try {
      setLoading(true);
      const response = await ApiService.getAllPromptTemplates();
      setTemplates(response.templates || []);
    } catch (error) {
      console.error('Error loading templates:', error);
      alert('Failed to load prompt templates');
    } finally {
      setLoading(false);
    }
  };

  const loadCategories = async () => {
    try {
      const response = await ApiService.getPromptCategories();
      setCategories(response.categories || []);
    } catch (error) {
      console.error('Error loading categories:', error);
    }
  };

  const handleDeleteTemplate = async (templateId: string) => {
    setTemplateToDelete(templateId);
    setShowDeleteConfirm(true);
  };

  const confirmDelete = async () => {
    if (!templateToDelete) return;

    try {
      await ApiService.deletePromptTemplate(templateToDelete);
      alert('Prompt template deleted successfully');
      loadTemplates();
    } catch (error) {
      console.error('Error deleting template:', error);
      alert('Failed to delete prompt template');
    } finally {
      setShowDeleteConfirm(false);
      setTemplateToDelete(null);
    }
  };

  const cancelDelete = () => {
    setShowDeleteConfirm(false);
    setTemplateToDelete(null);
  };

  const handleRestoreTemplate = async (templateId: string) => {
    try {
      await ApiService.restorePromptTemplate(templateId);
      alert('Prompt template restored successfully');
      loadTemplates();
    } catch (error) {
      console.error('Error restoring template:', error);
      alert('Failed to restore prompt template');
    }
  };

  const handleDuplicateTemplate = async (template: PromptTemplate) => {
    if (!template.id) return;
    
    const newName = prompt('Enter name for the duplicated template:', `${template.name} (Copy)`);
    if (!newName) return;

    try {
      await ApiService.duplicatePromptTemplate(template.id, newName);
      alert('Prompt template duplicated successfully');
      loadTemplates();
    } catch (error) {
      console.error('Error duplicating template:', error);
      alert('Failed to duplicate prompt template');
    }
  };

  const filteredTemplates = templates.filter(template => {
    const matchesSearch = template.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         (template.description?.toLowerCase() || '').includes(searchTerm.toLowerCase()) ||
                         template.category.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesCategory = !selectedCategory || template.category === selectedCategory;
    
    const matchesActiveFilter = showInactiveTemplates || template.is_active;

    return matchesSearch && matchesCategory && matchesActiveFilter;
  });

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getCategoryColor = (category: string) => {
    const colors = {
      'RAG': 'bg-blue-100 text-blue-800',
      'Chat': 'bg-green-100 text-green-800',
      'Document': 'bg-purple-100 text-purple-800',
      'Analysis': 'bg-orange-100 text-orange-800',
      'Default': 'bg-gray-100 text-gray-800'
    };
    return colors[category as keyof typeof colors] || colors.Default;
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-center h-48">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="p-6 border-b border-gray-200">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <h2 className="text-xl font-semibold text-gray-900">
            Prompt Templates ({filteredTemplates.length})
          </h2>
          <button 
            onClick={onCreateNew}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            + Create Template
          </button>
        </div>
        
        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-4 mt-4">
          <div className="relative flex-1">
            <input
              type="text"
              placeholder="Search templates..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">All Categories</option>
            {categories.map(category => (
              <option key={category} value={category}>{category}</option>
            ))}
          </select>
          
          <label className="flex items-center gap-2 text-sm text-gray-600 whitespace-nowrap">
            <input
              type="checkbox"
              checked={showInactiveTemplates}
              onChange={(e) => setShowInactiveTemplates(e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            Show Inactive
          </label>
        </div>
      </div>

      <div className="divide-y divide-gray-200">
        {filteredTemplates.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <p className="text-lg font-medium mb-2">No prompt templates found</p>
            <p className="text-sm">
              {searchTerm || selectedCategory ? 
                'Try adjusting your search or filter criteria.' : 
                'Create your first prompt template to get started.'
              }
            </p>
          </div>
        ) : (
          filteredTemplates.map((template) => (
            <div
              key={template.id}
              className={`p-6 hover:bg-gray-50 transition-colors cursor-pointer ${
                selectedTemplateId === template.id ? 'bg-blue-50 border-l-4 border-blue-500' : ''
              } ${!template.is_active ? 'opacity-60 bg-gray-50' : ''}`}
              onClick={() => onSelectTemplate(template)}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-2 flex-wrap">
                    <h3 className="text-lg font-medium text-gray-900">
                      {template.name}
                    </h3>
                    <span className={`px-2 py-1 text-xs rounded-full ${getCategoryColor(template.category)}`}>
                      {template.category}
                    </span>
                    {!template.is_active && (
                      <span className="px-2 py-1 text-xs rounded-full bg-red-100 text-red-800">
                        Inactive
                      </span>
                    )}
                    <span className="text-sm text-gray-500">
                      v{template.version}
                    </span>
                  </div>
                  
                  <p className="text-sm text-gray-600 mb-3">
                    {template.description}
                  </p>
                  
                  <div className="flex items-center gap-4 text-xs text-gray-500 flex-wrap">
                    <span>Created by: {template.created_by || 'Unknown'}</span>
                    {template.updated_at && (
                      <span>Updated: {formatDate(template.updated_at)}</span>
                    )}
                    {template.variables && template.variables.length > 0 && (
                      <span>{template.variables.length} variables</span>
                    )}
                    {template.placeholders && template.placeholders.length > 0 && (
                      <span>{template.placeholders.length} placeholders</span>
                    )}
                  </div>
                </div>
                
                <div className="flex items-center gap-2 ml-4">
                  <button
                    onClick={(e: React.MouseEvent) => {
                      e.stopPropagation();
                      onSelectTemplate(template);
                    }}
                    className="px-3 py-1 text-sm text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded"
                    title="Edit Template"
                  >
                    Edit
                  </button>
                  
                  <button
                    onClick={(e: React.MouseEvent) => {
                      e.stopPropagation();
                      handleDuplicateTemplate(template);
                    }}
                    className="px-3 py-1 text-sm text-green-600 hover:text-green-700 hover:bg-green-50 rounded"
                    title="Duplicate Template"
                  >
                    Copy
                  </button>
                  
                  {template.is_active ? (
                    <button
                      onClick={(e: React.MouseEvent) => {
                        e.stopPropagation();
                        if (template.id) {
                          handleDeleteTemplate(template.id);
                        }
                      }}
                      className="px-3 py-1 text-sm text-red-600 hover:text-red-700 hover:bg-red-50 rounded"
                      title="Delete Template"
                    >
                      Delete
                    </button>
                  ) : (
                    <button
                      onClick={(e: React.MouseEvent) => {
                        e.stopPropagation();
                        if (template.id) {
                          handleRestoreTemplate(template.id);
                        }
                      }}
                      className="px-3 py-1 text-sm text-green-600 hover:text-green-700 hover:bg-green-50 rounded"
                      title="Restore Template"
                    >
                      Restore
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
      
      <ConfirmDialog
        isOpen={showDeleteConfirm}
        title="Delete Prompt Template"
        message="Are you sure you want to delete this prompt template? This action cannot be undone."
        onConfirm={confirmDelete}
        onCancel={cancelDelete}
      />
    </div>
  );
};

export default PromptTemplateList;
