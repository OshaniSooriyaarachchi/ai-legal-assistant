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

interface Category {
  value: string;
  label: string;
}

interface UserType {
  value: string;
  label: string;
}

interface PromptTemplateEditorProps {
  prompt: PromptTemplate | null;
  categories: Category[];
  userTypes: UserType[];
  isCreating: boolean;
  onSave: (promptData: any) => void;
  onCancel: () => void;
}

const PromptTemplateEditor: React.FC<PromptTemplateEditorProps> = ({
  prompt,
  categories,
  userTypes,
  isCreating,
  onSave,
  onCancel
}) => {
  const [formData, setFormData] = useState<PromptTemplate>({
    name: '',
    title: '',
    description: '',
    template_content: '',
    placeholders: [],
    category: 'system',
    user_type: 'all',
    is_active: true
  });
  const [testVariables, setTestVariables] = useState<Record<string, string>>({});
  const [testResult, setTestResult] = useState<string | null>(null);
  const [testError, setTestError] = useState<string | null>(null);
  const [isTestingPrompt, setIsTestingPrompt] = useState(false);

  useEffect(() => {
    if (prompt) {
      setFormData({
        name: prompt.name,
        title: prompt.title,
        description: prompt.description || '',
        template_content: prompt.template_content || '',
        placeholders: prompt.placeholders || [],
        category: prompt.category,
        user_type: prompt.user_type,
        is_active: prompt.is_active
      });
      
      // Initialize test variables for existing placeholders
      const initialTestVars: Record<string, string> = {};
      (prompt.placeholders || []).forEach(placeholder => {
        initialTestVars[placeholder] = getDefaultTestValue(placeholder);
      });
      setTestVariables(initialTestVars);
    }
  }, [prompt]);

  const getDefaultTestValue = (placeholder: string): string => {
    const defaults: Record<string, string> = {
      'query': 'What are my rights as a tenant?',
      'context': 'Sample legal document content about tenant rights...',
      'document_text': 'This is a sample legal document for testing purposes.',
      'message': 'I need help with a legal contract',
      'conversation_history': 'Previous conversation context...',
      'session_context': 'Current session context...'
    };
    return defaults[placeholder] || `Sample ${placeholder}`;
  };

  const extractPlaceholders = (content: string): string[] => {
    const regex = /{([^}]+)}/g;
    const placeholders: string[] = [];
    let match;
    while ((match = regex.exec(content)) !== null) {
      if (!placeholders.includes(match[1])) {
        placeholders.push(match[1]);
      }
    }
    return placeholders;
  };

  const handleContentChange = (content: string) => {
    const newPlaceholders = extractPlaceholders(content);
    
    setFormData(prev => ({
      ...prev,
      template_content: content,
      placeholders: newPlaceholders
    }));

    // Update test variables for new placeholders
    const updatedTestVars = { ...testVariables };
    newPlaceholders.forEach(placeholder => {
      if (!(placeholder in updatedTestVars)) {
        updatedTestVars[placeholder] = getDefaultTestValue(placeholder);
      }
    });
    
    // Remove test variables for removed placeholders
    Object.keys(updatedTestVars).forEach(key => {
      if (!newPlaceholders.includes(key)) {
        delete updatedTestVars[key];
      }
    });
    
    setTestVariables(updatedTestVars);
  };

    const handleTest = async () => {
    try {
      setIsTestingPrompt(true);
      const testData = {
        template_content: formData.template_content,
        variables: testVariables
      };
      
      const response = await ApiService.testPromptTemplate(testData);
      setTestResult(response.data?.output || 'Test completed successfully');
    } catch (error) {
      console.error('Test failed:', error);
      setTestResult('Test failed. Please check your template and try again.');
    } finally {
      setIsTestingPrompt(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-800">
            {isCreating ? 'Create New Prompt Template' : 'Edit Prompt Template'}
          </h1>
          <button
            onClick={onCancel}
            className="bg-gray-500 hover:bg-gray-600 text-white px-4 py-2 rounded-lg transition-colors"
          >
            Cancel
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Basic Information */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold mb-4">Basic Information</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Name *
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="e.g., rag_prompt"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                  disabled={!isCreating} // Can't change name after creation
                />
                {!isCreating && (
                  <p className="text-sm text-gray-500 mt-1">Name cannot be changed after creation</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Title *
                </label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
                  placeholder="e.g., RAG Question Answering"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Category *
                </label>
                <select
                  value={formData.category}
                  onChange={(e) => setFormData(prev => ({ ...prev, category: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                >
                  {categories.length > 0 ? (
                    categories.map((category) => (
                      <option key={category.value} value={category.value}>
                        {category.label}
                      </option>
                    ))
                  ) : (
                    <option value="system">System</option>
                  )}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  User Type *
                </label>
                <select
                  value={formData.user_type}
                  onChange={(e) => setFormData(prev => ({ ...prev, user_type: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                >
                  {userTypes.length > 0 ? (
                    userTypes.map((userType) => (
                      <option key={userType.value} value={userType.value}>
                        {userType.label}
                      </option>
                    ))
                  ) : (
                    <option value="all">All</option>
                  )}
                </select>
              </div>
            </div>

            <div className="mt-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Description
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                placeholder="Describe what this prompt template is used for..."
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="mt-4">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={formData.is_active}
                  onChange={(e) => setFormData(prev => ({ ...prev, is_active: e.target.checked }))}
                  className="mr-2"
                />
                <span className="text-sm text-gray-700">Active (template is available for use)</span>
              </label>
            </div>
          </div>

          {/* Template Content */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold mb-4">Template Content</h2>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Prompt Template *
              </label>
              <textarea
                value={formData.template_content}
                onChange={(e) => handleContentChange(e.target.value)}
                placeholder="Enter your prompt template with placeholders like {query}, {context}, etc."
                rows={15}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                required
              />
              <p className="text-sm text-gray-500 mt-2">
                Use curly braces for placeholders: {'{query}'}, {'{context}'}, etc.
              </p>
            </div>

            {/* Detected Placeholders */}
            {formData.placeholders && formData.placeholders.length > 0 && (
              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Detected Placeholders
                </label>
                <div className="flex flex-wrap gap-2">
                  {formData.placeholders.map((placeholder, index) => (
                    <span
                      key={index}
                      className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm"
                    >
                      {'{' + placeholder + '}'}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Test Section */}
          {formData.placeholders && formData.placeholders.length > 0 && (
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold mb-4">Test Template</h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                {formData.placeholders.map((placeholder) => (
                  <div key={placeholder}>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      {placeholder}
                    </label>
                    <textarea
                      value={testVariables[placeholder] || ''}
                      onChange={(e) => setTestVariables(prev => ({
                        ...prev,
                        [placeholder]: e.target.value
                      }))}
                      rows={3}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                    />
                  </div>
                ))}
              </div>

              <button
                type="button"
                onClick={handleTest}
                disabled={isTestingPrompt}
                className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg transition-colors disabled:opacity-50"
              >
                {isTestingPrompt ? 'Testing...' : 'Test Prompt'}
              </button>

              {testError && (
                <div className="mt-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
                  <strong>Test Error:</strong> {testError}
                </div>
              )}

              {testResult && (
                <div className="mt-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Formatted Result
                  </label>
                  <div className="bg-gray-100 border border-gray-300 rounded-md p-4 max-h-96 overflow-y-auto">
                    <pre className="whitespace-pre-wrap text-sm">{testResult}</pre>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Submit Buttons */}
          <div className="flex justify-end space-x-4">
            <button
              type="button"
              onClick={onCancel}
              className="bg-gray-500 hover:bg-gray-600 text-white px-6 py-2 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded-lg transition-colors"
            >
              {isCreating ? 'Create Template' : 'Update Template'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default PromptTemplateEditor;
