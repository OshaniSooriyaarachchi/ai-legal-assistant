// Use environment variable for backend URL
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

export class ApiService {
  private static baseURL = API_BASE_URL;

  // Chat endpoints
  static async sendChatMessage(query: string, sessionId?: string) {
    const url = sessionId
      ? `${this.baseURL}/api/chat/sessions/${sessionId}/message`
      : `${this.baseURL}/api/chat`;
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
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

    const response = await fetch(url, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  static async getDocuments() {
    const response = await fetch(`${this.baseURL}/api/documents`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  static async deleteDocument(documentId: string) {
    const response = await fetch(`${this.baseURL}/api/documents/${documentId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  // Chat session endpoints
  static async createChatSession(title?: string) {
    const response = await fetch(`${this.baseURL}/api/chat/sessions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ title }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  static async getChatSessions() {
    const response = await fetch(`${this.baseURL}/api/chat/sessions`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  static async getChatHistory(sessionId: string) {
    const response = await fetch(`${this.baseURL}/api/chat/sessions/${sessionId}/history`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  static async getSessionDocuments(sessionId: string) {
    const response = await fetch(`${this.baseURL}/api/chat/sessions/${sessionId}/documents`);
    
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
