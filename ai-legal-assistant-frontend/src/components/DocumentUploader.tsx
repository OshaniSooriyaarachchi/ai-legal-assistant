import React, { useState } from 'react';
import { useAppDispatch } from '../app/hooks';
import { uploadDocument } from '../features/chat/chatSlice';
import { loadDocuments } from '../features/documents/documentsSlice';

const DocumentUploader: React.FC = () => {
  const dispatch = useAppDispatch();
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [displayName, setDisplayName] = useState('');
  const [description, setDescription] = useState('');
  const [errors, setErrors] = useState<{[key: string]: string}>({});

  const validateForm = () => {
    const newErrors: {[key: string]: string} = {};
    
    if (!file) {
      newErrors.file = 'Please select a file';
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

  const handleFileChange = (files: FileList | null) => {
    if (!files || !files[0]) return;
    
    const selectedFile = files[0];
    
    // Validate file type
    const allowedTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'];
    if (!allowedTypes.includes(selectedFile.type)) {
      setErrors({...errors, file: 'Only PDF, DOCX, and TXT files are supported'});
      return;
    }
    
    setFile(selectedFile);
    setErrors({...errors, file: ''});
    
    // Auto-populate display name with filename if empty
    if (!displayName) {
      setDisplayName(selectedFile.name.replace(/\.[^/.]+$/, ''));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) return;
    
    setUploading(true);
    try {
      // Use the existing uploadDocument action with the new structure
      const result = await dispatch(uploadDocument({ 
        file: file!, 
        displayName: displayName.trim(), 
        description: description.trim() 
      })).unwrap();
      console.log('Upload successful:', result);
      
      // Reset form
      setFile(null);
      setDisplayName('');
      setDescription('');
      setErrors({});
      
      // Refresh documents list
      dispatch(loadDocuments());
      
    } catch (error) {
      console.error('Upload failed:', error);
      setErrors({submit: 'Upload failed. Please try again.'});
    } finally {
      setUploading(false);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files) {
      handleFileChange(e.dataTransfer.files);
    }
  };

  return (
    <div className="w-full max-w-lg mx-auto">
      <form onSubmit={handleSubmit} className="space-y-6">
        
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
            Select File *
          </label>
          <div
            className={`relative border-2 border-dashed rounded-lg p-6 transition-colors ${
              dragActive ? 'border-blue-400 bg-blue-50' : 
              errors.file ? 'border-red-400' : 'border-gray-300'
            }`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <input
              type="file"
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              onChange={(e) => handleFileChange(e.target.files)}
              accept=".pdf,.docx,.txt"
              disabled={uploading}
            />
            
            <div className="text-center">
              {file ? (
                <div>
                  <div className="text-sm text-gray-600">
                    <p className="font-medium">{file.name}</p>
                    <p>{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                  </div>
                </div>
              ) : (
                <div>
                  <svg className="mx-auto h-12 w-12 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48">
                    <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  <p className="mt-2 text-sm text-gray-600">
                    Drop your document here or click to browse
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

        {/* Submit Button */}
        <div>
          <button
            type="submit"
            disabled={uploading}
            className={`w-full py-2 px-4 rounded-md font-medium ${
              uploading
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            {uploading ? (
              <div className="flex items-center justify-center">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Uploading and processing...
              </div>
            ) : (
              'Upload Document'
            )}
          </button>
        </div>

        {errors.submit && (
          <p className="text-sm text-red-600 text-center">{errors.submit}</p>
        )}
      </form>
    </div>
  );
};

export default DocumentUploader;