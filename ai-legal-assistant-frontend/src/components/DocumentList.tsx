import React, { useEffect } from 'react';
import { useAppDispatch, useAppSelector } from '../app/hooks';
import { loadDocuments, deleteDocument } from '../features/documents/documentsSlice';

const DocumentList: React.FC = () => {
  const dispatch = useAppDispatch();
  const { documents, loading, error } = useAppSelector((state) => state.documents);

  useEffect(() => {
    dispatch(loadDocuments());
  }, [dispatch]);

  const handleDelete = async (documentId: string) => {
    if (window.confirm('Are you sure you want to delete this document?')) {
      try {
        await dispatch(deleteDocument(documentId)).unwrap();
      } catch (error) {
        console.error('Delete failed:', error);
      }
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-32">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4">
        <p className="text-red-800">Error loading documents: {error}</p>
      </div>
    );
  }

  return (
    <div className="bg-white shadow overflow-hidden sm:rounded-md">
      <ul className="divide-y divide-gray-200">
        {documents.map((doc) => (
          <li key={doc.id}>
            <div className="px-4 py-4 flex items-center justify-between">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className="h-8 w-8 bg-blue-100 rounded-full flex items-center justify-center">
                    <svg className="h-4 w-4 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                    </svg>
                  </div>
                </div>
                <div className="ml-4">
                  <div className="text-sm font-medium text-gray-900">{doc.filename}</div>
                  <div className="text-sm text-gray-500">
                    Status: <span className={`capitalize ${doc.status === 'completed' ? 'text-green-600' : 'text-yellow-600'}`}>
                      {doc.status}
                    </span>
                  </div>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => handleDelete(doc.id)}
                  className="text-red-600 hover:text-red-800 text-sm"
                >
                  Delete
                </button>
              </div>
            </div>
          </li>
        ))}
      </ul>
      {documents.length === 0 && (
        <div className="text-center py-8">
          <p className="text-gray-500">No documents uploaded yet</p>
        </div>
      )}
    </div>
  );
};

export default DocumentList;