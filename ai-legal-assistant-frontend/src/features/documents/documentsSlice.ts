import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';

interface Document {
  id: string;
  filename: string;
  status: string;
  upload_date: string;
  file_size: number;
}

interface DocumentsState {
  documents: Document[];
  loading: boolean;
  error: string | null;
}

const initialState: DocumentsState = {
  documents: [],
  loading: false,
  error: null,
};

export const uploadDocument = createAsyncThunk(
  'documents/upload',
  async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch('/api/documents/upload', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error('Upload failed');
    }

    return response.json();
  }
);

export const fetchDocuments = createAsyncThunk(
  'documents/fetchAll',
  async () => {
    const response = await fetch('/api/documents');
    if (!response.ok) {
      throw new Error('Failed to fetch documents');
    }
    return response.json();
  }
);

export const deleteDocument = createAsyncThunk(
  'documents/delete',
  async (documentId: string) => {
    const response = await fetch(`/api/documents/${documentId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error('Delete failed');
    }

    return documentId;
  }
);

const documentsSlice = createSlice({
  name: 'documents',
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(uploadDocument.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(uploadDocument.fulfilled, (state, action) => {
        state.loading = false;
        // Refresh documents list after upload
      })
      .addCase(uploadDocument.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Upload failed';
      })
      .addCase(fetchDocuments.pending, (state) => {
        state.loading = true;
      })
      .addCase(fetchDocuments.fulfilled, (state, action) => {
        state.loading = false;
        state.documents = action.payload.documents || [];
      })
      .addCase(fetchDocuments.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch documents';
      })
      .addCase(deleteDocument.fulfilled, (state, action) => {
        state.documents = state.documents.filter(doc => doc.id !== action.payload);
      });
  },
});

export default documentsSlice.reducer;