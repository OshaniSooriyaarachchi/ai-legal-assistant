// Import supabase client for auth
import { supabase } from '../lib/supabase';

// Use environment variable for backend URL
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

export class ApiService {
  private static baseURL = API_BASE_URL;

  // Get authentication headers
  private static async getAuthHeaders(): Promise<Record<string, string>> {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      
      if (session?.access_token) {
        return {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        };
      }
    } catch (error) {
      console.error('Error getting auth session:', error);
    }
    
    return {
      'Content-Type': 'application/json',
    };
  }

  // Get auth headers for form data
  private static async getAuthHeadersForFormData(): Promise<Record<string, string>> {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      
      if (session?.access_token) {
        return {
          'Authorization': `Bearer ${session.access_token}`,
        };
      }
    } catch (error) {
      console.error('Error getting auth session:', error);
    }
    
    return {};
  }

  // Chat endpoints
  static async sendChatMessage(query: string, sessionId?: string) {
    const url = sessionId
      ? `${this.baseURL}/api/chat/sessions/${sessionId}/message`
      : `${this.baseURL}/api/chat`;
    
    const headers = await this.getAuthHeaders();
    
    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify({ query }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  // Document endpoints
  static async uploadDocument(file: File, sessionId?: string) {
    const formData = new FormData();
    formData.append('file', file);

    const url = sessionId 
      ? `${this.baseURL}/api/chat/sessions/${sessionId}/upload`
      : `${this.baseURL}/api/documents/upload`;

    const headers = await this.getAuthHeadersForFormData();

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  static async getDocuments() {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/documents`, {
      headers,
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  static async deleteDocument(documentId: string) {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/documents/${documentId}`, {
      method: 'DELETE',
      headers,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  // Chat session endpoints
  static async createChatSession(title?: string) {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/chat/sessions`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ title }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  static async getChatSessions() {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/chat/sessions`, {
      headers,
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  static async getChatHistory(sessionId: string) {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/chat/sessions/${sessionId}/history`, {
      headers,
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  static async getSessionDocuments(sessionId: string) {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/chat/sessions/${sessionId}/documents`, {
      headers,
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  static async deleteChatSession(sessionId: string) {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/chat/sessions/${sessionId}`, {
      method: 'DELETE',
      headers,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  static async clearChatHistory(sessionId: string) {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/chat/sessions/${sessionId}/history`, {
      method: 'DELETE',
      headers,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  // Health check endpoint
  static async checkHealth() {
    const response = await fetch(`${this.baseURL}/health`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }
}
