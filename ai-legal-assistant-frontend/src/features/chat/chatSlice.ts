import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';

interface Message {
  id: string;
  content: string;
  sender: 'user' | 'assistant';
  timestamp: string;
  type?: 'text' | 'document';
  fileName?: string;
}

interface UploadedDocument {
  id: string;
  fileName: string;
  uploadedAt: string;
}

interface ChatState {
  messages: Message[];
  uploadedDocuments: UploadedDocument[];
  loading: boolean;
  uploading: boolean;
  error: string | null;
}

const initialState: ChatState = {
  messages: [],
  uploadedDocuments: [],
  loading: false,
  uploading: false,
  error: null,
};

export const sendMessage = createAsyncThunk(
  'chat/sendMessage',
  async (query: string) => {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query }),
    });

    if (!response.ok) {
      throw new Error('Failed to send message');
    }

    return response.json();
  }
);

export const uploadDocument = createAsyncThunk(
  'chat/uploadDocument',
  async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch('/api/documents/upload', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error('Failed to upload document');
    }

    const result = await response.json();
    return {
      id: result.document_id,
      fileName: file.name,
      uploadedAt: new Date().toISOString(),
    };
  }
);

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    clearChat: (state) => {
      state.messages = [];
      state.uploadedDocuments = [];
    },
    addDocumentMessage: (state, action) => {
      const documentMessage: Message = {
        id: Date.now().toString(),
        content: `Document "${action.payload.fileName}" uploaded successfully`,
        sender: 'assistant',
        timestamp: new Date().toISOString(),
        type: 'document',
        fileName: action.payload.fileName,
      };
      state.messages.push(documentMessage);
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(sendMessage.pending, (state, action) => {
        const userMessage: Message = {
          id: Date.now().toString(),
          content: action.meta.arg,
          sender: 'user',
          timestamp: new Date().toISOString(),
          type: 'text',
        };
        state.messages.push(userMessage);
        state.loading = true;
        state.error = null;
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        state.loading = false;
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: action.payload.response,
          sender: 'assistant',
          timestamp: new Date().toISOString(),
          type: 'text',
        };
        state.messages.push(assistantMessage);
      })
      .addCase(sendMessage.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to send message';
      })
      .addCase(uploadDocument.pending, (state) => {
        state.uploading = true;
        state.error = null;
      })
      .addCase(uploadDocument.fulfilled, (state, action) => {
        state.uploading = false;
        state.uploadedDocuments.push(action.payload);
        
        // Add a system message about the upload
        const uploadMessage: Message = {
          id: Date.now().toString(),
          content: `📄 Document "${action.payload.fileName}" uploaded successfully. You can now ask questions about it.`,
          sender: 'assistant',
          timestamp: new Date().toISOString(),
          type: 'document',
          fileName: action.payload.fileName,
        };
        state.messages.push(uploadMessage);
      })
      .addCase(uploadDocument.rejected, (state, action) => {
        state.uploading = false;
        state.error = action.error.message || 'Failed to upload document';
        
        // Add error message
        const errorMessage: Message = {
          id: Date.now().toString(),
          content: `❌ Failed to upload document: ${action.error.message}`,
          sender: 'assistant',
          timestamp: new Date().toISOString(),
          type: 'text',
        };
        state.messages.push(errorMessage);
      });
  },
});

export const { clearChat, addDocumentMessage } = chatSlice.actions;
export default chatSlice.reducer;