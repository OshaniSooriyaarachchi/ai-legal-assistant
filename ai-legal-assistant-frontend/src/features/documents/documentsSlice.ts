import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { ApiService } from '../../services/api';

interface Document {
  id: string;
  filename: string;
  status: string;
  upload_date: string;
  file_size: number;
  source_type: string;
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

export const loadDocuments = createAsyncThunk(
  'documents/loadDocuments',
  async () => {
    const response = await ApiService.getDocuments();
    return response.documents || [];
  }
);

export const deleteDocument = createAsyncThunk(
  'documents/deleteDocument',
  async (documentId: string) => {
    await ApiService.deleteDocument(documentId);
    return documentId;
  }
);

const documentsSlice = createSlice({
  name: 'documents',
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(loadDocuments.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(loadDocuments.fulfilled, (state, action) => {
        state.documents = action.payload;
        state.loading = false;
      })
      .addCase(loadDocuments.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to load documents';
      })
      .addCase(deleteDocument.fulfilled, (state, action) => {
        state.documents = state.documents.filter(doc => doc.id !== action.payload);
      });
  },
});

export default documentsSlice.reducer;