import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { ApiService } from '../../services/api';

interface Message {
  id: string;
  content: string;
  sender: 'user' | 'assistant';
  timestamp: string;
  type?: 'text' | 'document';
  fileName?: string;
  sources?: any[];
}

interface UploadedDocument {
  id: string;
  fileName: string;
  uploadedAt: string;
}

interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

interface ChatState {
  messages: Message[];
  uploadedDocuments: UploadedDocument[];
  sessions: ChatSession[];
  currentSessionId: string | null;
  loading: boolean;
  uploading: boolean;
  error: string | null;
}

const initialState: ChatState = {
  messages: [],
  uploadedDocuments: [],
  sessions: [],
  currentSessionId: null,
  loading: false,
  uploading: false,
  error: null,
};

export const sendMessage = createAsyncThunk(
  'chat/sendMessage',
  async (query: string, { getState }) => {
    const state = getState() as { chat: ChatState };
    const sessionId = state.chat.currentSessionId;
    
    const response = await ApiService.sendChatMessage(query, sessionId || undefined);
    return {
      query,
      response: response.response,
      sources: response.sources || [],
      sessionId
    };
  }
);

export const uploadDocument = createAsyncThunk(
  'chat/uploadDocument',
  async (file: File, { getState }) => {
    const state = getState() as { chat: ChatState };
    const sessionId = state.chat.currentSessionId;
    
    const result = await ApiService.uploadDocument(file, sessionId || undefined);
    return {
      id: result.document_id,
      fileName: file.name,
      uploadedAt: new Date().toISOString(),
    };
  }
);

export const createChatSession = createAsyncThunk(
  'chat/createSession',
  async (title?: string) => {
    const response = await ApiService.createChatSession(title);
    return response;
  }
);

export const loadChatSessions = createAsyncThunk(
  'chat/loadSessions',
  async () => {
    const response = await ApiService.getChatSessions();
    return response.sessions || [];
  }
);

export const loadChatHistory = createAsyncThunk(
  'chat/loadHistory',
  async (sessionId: string) => {
    const response = await ApiService.getChatHistory(sessionId);
    return {
      sessionId,
      messages: response.messages || []
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
    setCurrentSession: (state, action) => {
      state.currentSessionId = action.payload;
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
      // Send message cases
      .addCase(sendMessage.pending, (state, action) => {
        const userMessage: Message = {
          id: Date.now().toString(),
          content: action.meta.arg,
          sender: 'user',
          timestamp: new Date().toISOString(),
        };
        state.messages.push(userMessage);
        state.loading = true;
        state.error = null;
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: action.payload.response,
          sender: 'assistant',
          timestamp: new Date().toISOString(),
          sources: action.payload.sources,
        };
        state.messages.push(assistantMessage);
        state.loading = false;
      })
      .addCase(sendMessage.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to send message';
      })
      
      // Upload document cases
      .addCase(uploadDocument.pending, (state) => {
        state.uploading = true;
        state.error = null;
      })
      .addCase(uploadDocument.fulfilled, (state, action) => {
        state.uploadedDocuments.push(action.payload);
        state.uploading = false;
        chatSlice.caseReducers.addDocumentMessage(state, {
          type: 'chat/addDocumentMessage',
          payload: action.payload
        });
      })
      .addCase(uploadDocument.rejected, (state, action) => {
        state.uploading = false;
        state.error = action.error.message || 'Failed to upload document';
      })
      
      // Session management cases
      .addCase(createChatSession.fulfilled, (state, action) => {
        state.sessions.push(action.payload);
        state.currentSessionId = action.payload.id;
        state.messages = []; // Clear messages for new session
      })
      .addCase(loadChatSessions.fulfilled, (state, action) => {
        state.sessions = action.payload;
      })
      .addCase(loadChatHistory.fulfilled, (state, action) => {
        if (action.payload.sessionId === state.currentSessionId) {
          state.messages = action.payload.messages;
        }
      });
  },
});

export const { clearChat, setCurrentSession, addDocumentMessage } = chatSlice.actions;
export default chatSlice.reducer;