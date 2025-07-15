export interface ChatMessage {
  id: string;
  content: string;
  sender: 'user' | 'assistant';
  timestamp: string;
  type?: 'text' | 'document';
  fileName?: string;
  sources?: any[];
}

export interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface UploadedDocument {
  id: string;
  fileName: string;
  uploadedAt: string;
}

export interface ChatState {
  messages: ChatMessage[];
  uploadedDocuments: UploadedDocument[];
  sessions: ChatSession[];
  currentSessionId: string | null;
  loading: boolean;
  uploading: boolean;
  isLoadingSessions: boolean;
  error: string | null;
}
