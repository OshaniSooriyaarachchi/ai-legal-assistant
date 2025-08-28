import React, { useState } from 'react';
import { supabase } from '../../lib/supabase';

const DocumentUploadAdmin: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [category, setCategory] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [description, setDescription] = useState('');
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [errors, setErrors] = useState<{[key: string]: string}>({});

  const categories = [
    { value: 'traffic_law', label: 'Traffic Law' },
    { value: 'criminal_law', label: 'Criminal Law' },
    { value: 'civil_law', label: 'Civil Law' },
    { value: 'commercial_law', label: 'Commercial Law' },
    { value: 'constitutional_law', label: 'Constitutional Law' },
    { value: 'labor_law', label: 'Labor Law' },
    { value: 'family_law', label: 'Family Law' },
    { value: 'other', label: 'Other' },
  ];

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      setFile(selectedFile);
      
      // Auto-populate display name with filename if empty
      if (!displayName) {
        setDisplayName(selectedFile.name.replace(/\.[^/.]+$/, ''));
      }
    }
  };

  const validateForm = () => {
    const newErrors: {[key: string]: string} = {};
    
    if (!file) {
      newErrors.file = 'Please select a file';
    }
    
    if (!category) {
      newErrors.category = 'Please select a category';
    }
    
    if (!displayName.trim()) {
      newErrors.displayName = 'Document name is required';
    }
    
    if (!description.trim()) {
      newErrors.description = 'Document description is required';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleUpload = async () => {
    if (!validateForm()) {
      return;
    }

  setUploading(true);
  try {
    const formData = new FormData();
    formData.append('file', file!);
    formData.append('category', category);
    formData.append('display_name', displayName.trim());
    formData.append('description', description.trim());

    // Get auth headers
    const { data: { session } } = await supabase.auth.getSession();
    if (!session?.access_token) {
      throw new Error('No authentication token');
    }

    const response = await fetch('http://localhost:8000/api/admin/documents/upload', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${session.access_token}`,
      },
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Upload failed');
    }

    const data = await response.json();
    
    if (data.status === 'success') {
      alert('Document uploaded successfully to knowledge base!');
      setFile(null);
      setCategory('');
      setDisplayName('');
      setDescription('');
      setErrors({});
      // Reset file input
      const fileInput = document.getElementById('file-input') as HTMLInputElement;
      if (fileInput) fileInput.value = '';
    }
  } catch (error: any) {
    console.error('Upload error:', error);
    alert(error.message || 'Upload failed');
  } finally {
    setUploading(false);
  }
};

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-4">
          Upload Document to Knowledge Base
        </h3>
        <p className="text-sm text-gray-600 mb-6">
          Upload legal documents that will be available to all users in the knowledge base.
        </p>
      </div>

      {/* Category Selection */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Document Category *
        </label>
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className={`block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 ${
            errors.category ? 'border-red-500' : 'border-gray-300'
          }`}
          required
        >
          <option value="">Select a category</option>
          {categories.map((cat) => (
            <option key={cat.value} value={cat.value}>
              {cat.label}
            </option>
          ))}
        </select>
        {errors.category && (
          <p className="mt-1 text-sm text-red-600">{errors.category}</p>
        )}
      </div>

      {/* Document Name Field */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Document Name *
        </label>
        <input
          type="text"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 ${
            errors.displayName ? 'border-red-500' : 'border-gray-300'
          }`}
          placeholder="Enter a name for this document"
          disabled={uploading}
        />
        {errors.displayName && (
          <p className="mt-1 text-sm text-red-600">{errors.displayName}</p>
        )}
        <p className="mt-1 text-xs text-gray-500">
          This name will be used when referencing the document in responses
        </p>
      </div>

      {/* Description Field */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Document Description *
        </label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
          className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 ${
            errors.description ? 'border-red-500' : 'border-gray-300'
          }`}
          placeholder="Describe what this document contains"
          disabled={uploading}
        />
        {errors.description && (
          <p className="mt-1 text-sm text-red-600">{errors.description}</p>
        )}
      </div>

      {/* File Upload */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Legal Document *
        </label>
        <div
          className={`relative border-2 border-dashed rounded-lg p-6 text-center ${
            dragActive ? 'border-blue-400 bg-blue-50' : 
            errors.file ? 'border-red-400' : 'border-gray-300'
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <input
            id="file-input"
            type="file"
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            onChange={handleFileChange}
            accept=".pdf,.docx,.txt"
            disabled={uploading}
          />

          <div>
            {file ? (
              <div className="text-sm text-gray-600">
                <p className="font-medium">{file.name}</p>
                <p>{(file.size / 1024 / 1024).toFixed(2)} MB</p>
              </div>
            ) : (
              <div>
                <svg className="mx-auto h-12 w-12 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48">
                  <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <p className="mt-2 text-sm text-gray-600">
                  Drop your legal document here or click to browse
                </p>
                <p className="text-xs text-gray-500">PDF, DOCX, TXT up to 10MB</p>
              </div>
            )}
          </div>
        </div>
        {errors.file && (
          <p className="mt-1 text-sm text-red-600">{errors.file}</p>
        )}
      </div>

      {/* Upload Button */}
      <div>
        <button
          onClick={handleUpload}
          disabled={uploading}
          className={`w-full py-2 px-4 rounded-md font-medium ${
            uploading
              ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
              : 'bg-blue-600 text-white hover:bg-blue-700'
          }`}
        >
          {uploading ? 'Uploading...' : 'Upload to Knowledge Base'}
        </button>
      </div>
    </div>
  );
};

export default DocumentUploadAdmin;