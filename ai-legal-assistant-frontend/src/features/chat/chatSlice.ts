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
  isLoadingSessions: boolean;
  isDeletingSession: boolean;
  isClearingHistory: boolean;
  error: string | null;
}

const initialState: ChatState = {
  messages: [],
  uploadedDocuments: [],
  sessions: [],
  currentSessionId: null,
  loading: false,
  uploading: false,
  isLoadingSessions: false,
  isDeletingSession: false,
  isClearingHistory: false,
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
    const history = response.history || [];
    
    // Transform backend data to frontend Message format
    const messages: Message[] = [];
    
    history.forEach((item: any) => {
      // Handle new format (conversation type)
      if (item.message_type === 'conversation') {
        // Add user message
        if (item.query_text) {
          const userMsg = {
            id: `${item.id}-user`,
            content: item.query_text,
            sender: 'user' as const,
            timestamp: item.created_at,
            type: 'text' as const
          };
          messages.push(userMsg);
        }
        
        // Add assistant response
        if (item.response_text) {
          const assistantMsg = {
            id: `${item.id}-assistant`,
            content: item.response_text,
            sender: 'assistant' as const,
            timestamp: item.created_at,
            type: 'text' as const
          };
          messages.push(assistantMsg);
        }
      }
      // Handle old format (separate user_query and assistant_response)
      else if (item.message_type === 'user_query' && item.query_text) {
        const userMsg = {
          id: `${item.id}-user`,
          content: item.query_text,
          sender: 'user' as const,
          timestamp: item.created_at,
          type: 'text' as const
        };
        messages.push(userMsg);
      } 
      else if (item.message_type === 'assistant_response' && item.response_text) {
        const assistantMsg = {
          id: `${item.id}-assistant`,
          content: item.response_text,
          sender: 'assistant' as const,
          timestamp: item.created_at,
          type: 'text' as const
        };
        messages.push(assistantMsg);
      }
      // Handle document uploads
      else if (item.message_type === 'document_upload' && item.query_text) {
        const docMsg = {
          id: `${item.id}-document`,
          content: item.query_text,
          sender: 'assistant' as const,
          timestamp: item.created_at,
          type: 'document' as const
        };
        messages.push(docMsg);
      }
    });
    
    // Sort messages by timestamp to ensure proper order
    messages.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
    
    return {
      sessionId,
      messages
    };
  }
);

export const deleteChatSession = createAsyncThunk(
  'chat/deleteSession',
  async (sessionId: string) => {
    await ApiService.deleteChatSession(sessionId);
    return sessionId;
  }
);

export const clearChatHistory = createAsyncThunk(
  'chat/clearHistory',
  async (sessionId: string) => {
    await ApiService.clearChatHistory(sessionId);
    return sessionId;
  }
);

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    clearChatLocal: (state) => {
      // This is for local clearing only (e.g., when switching sessions)
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
        const timestamp = new Date().toISOString();
        const userMessage: Message = {
          id: `user-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          content: action.meta.arg,
          sender: 'user',
          timestamp,
        };
        
        // Check if this exact message already exists to prevent duplicates
        const isDuplicate = state.messages.some(msg => 
          msg.content === userMessage.content && 
          msg.sender === 'user' && 
          Math.abs(new Date(msg.timestamp).getTime() - new Date(timestamp).getTime()) < 2000 // Within 2 seconds
        );
        
        if (!isDuplicate) {
          state.messages.push(userMessage);
        }
        
        state.loading = true;
        state.error = null;
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        const assistantMessage: Message = {
          id: `assistant-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
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
      .addCase(loadChatSessions.pending, (state) => {
        state.isLoadingSessions = true;
      })
      .addCase(loadChatSessions.fulfilled, (state, action) => {
        state.sessions = action.payload;
        state.isLoadingSessions = false;
      })
      .addCase(loadChatSessions.rejected, (state) => {
        state.isLoadingSessions = false;
      })
      .addCase(loadChatHistory.fulfilled, (state, action) => {
        if (action.payload.sessionId === state.currentSessionId) {
          state.messages = action.payload.messages;
        }
      })
      .addCase(deleteChatSession.pending, (state) => {
        state.isDeletingSession = true;
        state.error = null;
      })
      .addCase(deleteChatSession.fulfilled, (state, action) => {
        // Remove the session from the sessions array
        state.sessions = state.sessions.filter(session => session.id !== action.payload);
        
        // If the deleted session was the current session, clear it
        if (state.currentSessionId === action.payload) {
          state.currentSessionId = null;
          state.messages = [];
        }
        
        state.isDeletingSession = false;
      })
      .addCase(deleteChatSession.rejected, (state, action) => {
        state.error = action.error.message || 'Failed to delete session';
        state.isDeletingSession = false;
      })
      .addCase(clearChatHistory.pending, (state) => {
        state.isClearingHistory = true;
        state.error = null;
      })
      .addCase(clearChatHistory.fulfilled, (state, action) => {
        // Clear messages for the session that was cleared
        if (state.currentSessionId === action.payload) {
          state.messages = [];
        }
        state.isClearingHistory = false;
      })
      .addCase(clearChatHistory.rejected, (state, action) => {
        state.error = action.error.message || 'Failed to clear chat history';
        state.isClearingHistory = false;
      });
  },
});

export const { clearChatLocal, setCurrentSession, addDocumentMessage } = chatSlice.actions;
export default chatSlice.reducer;