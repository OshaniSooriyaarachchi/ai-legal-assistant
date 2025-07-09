import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';

interface Message {
  id: string;
  content: string;
  sender: 'user' | 'assistant';
  timestamp: string;
}

interface ChatState {
  messages: Message[];
  loading: boolean;
  error: string | null;
}

const initialState: ChatState = {
  messages: [],
  loading: false,
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

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    clearChat: (state) => {
      state.messages = [];
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(sendMessage.pending, (state, action) => {
        // Add user message immediately
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
        state.loading = false;
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: action.payload.response,
          sender: 'assistant',
          timestamp: new Date().toISOString(),
        };
        state.messages.push(assistantMessage);
      })
      .addCase(sendMessage.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to send message';
      });
  },
});

export const { clearChat } = chatSlice.actions;
export default chatSlice.reducer;