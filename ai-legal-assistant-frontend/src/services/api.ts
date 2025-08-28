import { supabase } from '../lib/supabase';

// Use environment variable for backend URL
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || '';

// Subscription-related interfaces
export interface SubscriptionPlan {
  id: string;
  name: string;
  display_name: string;
  daily_query_limit: number;
  price_monthly: number;
  features: string[];
}

export interface UserSubscription {
  subscription_id: string;
  plan_name: string;
  plan_display_name: string;
  daily_limit: number;
  price_monthly?: number;
  features?: string[];
  status: string;
  expires_at?: string;
}

export interface UsageInfo {
  daily_usage: number;
  current_usage: number;
  daily_limit: number;
  remaining_queries: number;
  subscription: UserSubscription;
}

// Admin Package Management interfaces
export interface PackageFormData {
  name: string;
  display_name: string;
  daily_query_limit: number;
  max_document_size_mb: number;
  max_documents_per_user: number;
  price_monthly: number;
  features: string[];
  is_active: boolean;
}

export interface AdminPackage extends PackageFormData {
  id: string;
  created_at: string;
  updated_at: string;
  created_by: string;
  is_custom: boolean;
  active_subscriptions?: number;
  created_by_email?: string;
}

// Custom error class for rate limiting
export class RateLimitError extends Error {
  public readonly type = 'RATE_LIMIT';
  public readonly detail: any;

  constructor(detail: any) {
    super(detail.message || 'Rate limit exceeded');
    this.name = 'RateLimitError';
    this.detail = detail;
  }
}

export class ApiService {
  private static baseURL = API_BASE_URL;

  static async getAdminDocuments() {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/admin/documents`, {
      headers,
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  // Auth: Email/password signup hits backend to trigger verification email
  static async signupWithEmail(email: string, password: string) {
    const response = await fetch(`${this.baseURL}/api/auth/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Signup failed' }));
      throw new Error(err.detail || 'Signup failed');
    }
    return response.json();
  }

  static async getAdminStatistics() {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/admin/statistics`, {
      headers,
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  // Get authentication headers
  public static async getAuthHeaders(): Promise<Record<string, string>> {
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

  // Updated sendMessage method with rate limiting and user type
  static async sendMessage(sessionId: string, message: string, includePublic = true, userType = 'normal', includeUserDocs = true): Promise<any> {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/chat/sessions/${sessionId}/message`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        query: message,
        include_public: includePublic,
        include_user_docs: includeUserDocs,
        user_type: userType,
      }),
    });
    
    if (response.status === 429) {
      // Rate limit exceeded
      const errorData = await response.json();
      throw new RateLimitError(errorData.detail);
    }
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return response.json();
  }

  // Document endpoints
  static async uploadDocument(file: File, displayName: string, description: string, sessionId?: string) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('display_name', displayName);
    formData.append('description', description);

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

  // Chat session review endpoints
  static async getSessionReview(sessionId: string) {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/chat/sessions/${sessionId}/review`, { headers });
    if (!response.ok) {
      if (response.status === 404) {
        return { has_review: false };
      }
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  }

  static async submitSessionReview(sessionId: string, data: { rating?: number; comment?: string; skipped?: boolean }) {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/chat/sessions/${sessionId}/review`, {
      method: 'POST',
      headers,
      body: JSON.stringify(data)
    });
    if (response.status === 409) {
      return { alreadyExists: true };
    }
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

  static async updateSessionTitle(sessionId: string, title: string) {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/chat/sessions/${sessionId}/title`, {
      method: 'PUT',
      headers,
      body: JSON.stringify({ title })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  // Admin user chat endpoints
  static async getAllUserChats() {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/admin/users/chats`, {
      headers,
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  static async getUserChatsByAdmin(userId: string) {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/admin/users/${userId}/chats`, {
      headers,
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  static async getChatHistoryByAdmin(sessionId: string) {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/admin/sessions/${sessionId}/history`, {
      headers,
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  static async getAllUserDocuments() {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/admin/users/documents`, {
      headers,
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  static async getUserDocumentsByAdmin(userId: string) {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/admin/users/${userId}/documents`, {
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

  // Subscription management endpoints
  static async getSubscriptionPlans(): Promise<SubscriptionPlan[]> {
    const response = await fetch(`${this.baseURL}/api/subscription/plans`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    return data.plans;
  }

  static async getCurrentSubscription(): Promise<UsageInfo> {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/subscription/current`, {
      headers,
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return response.json();
  }

  static async upgradeSubscription(planName: string): Promise<void> {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/subscription/upgrade`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ plan_name: planName }),
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
  }

  static async getUsageHistory(days: number = 30) {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/usage/history?days=${days}`, {
      headers,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  // Admin Package Management endpoints
  static async getAdminPackages() {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/admin/packages`, {
      headers,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  static async createPackage(packageData: any) {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/admin/packages`, {
      method: 'POST',
      headers,
      body: JSON.stringify(packageData)
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  static async updatePackage(packageId: string, packageData: any) {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/admin/packages/${packageId}`, {
      method: 'PUT',
      headers,
      body: JSON.stringify(packageData)
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  static async deletePackage(packageId: string) {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/admin/packages/${packageId}`, {
      method: 'DELETE',
      headers,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  static async assignPackageToUser(userId: string, packageId: string) {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/admin/assign-package`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ user_id: userId, package_id: packageId })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  static async getUserUsageStats(userId: string) {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/admin/users/${userId}/usage`, {
      headers,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  // =============================================================================
  // PROMPT MANAGEMENT METHODS
  // =============================================================================

  static async getAllPromptTemplates() {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/admin/prompts`, {
      method: 'GET',
      headers,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  static async getPromptTemplate(templateId: string) {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/admin/prompts/${templateId}`, {
      method: 'GET',
      headers,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  static async createPromptTemplate(templateData: any) {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/admin/prompts`, {
      method: 'POST',
      headers,
      body: JSON.stringify(templateData)
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  static async updatePromptTemplate(templateId: string, templateData: any) {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/admin/prompts/${templateId}`, {
      method: 'PUT',
      headers,
      body: JSON.stringify(templateData)
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  static async deletePromptTemplate(templateId: string) {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/admin/prompts/${templateId}`, {
      method: 'DELETE',
      headers,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  static async restorePromptTemplate(templateId: string) {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/admin/prompts/${templateId}/restore`, {
      method: 'POST',
      headers,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  static async getPromptCategories() {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/admin/prompts/categories`, {
      method: 'GET',
      headers,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  static async getPromptUserTypes() {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/admin/prompts/user-types`, {
      method: 'GET',
      headers,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  static async testPromptTemplate(templateData: any) {
    // Format the template locally instead of calling the backend
    // This avoids the 422 error from mismatched request structure
    try {
      let formattedContent = templateData.template_content || '';
      
      // Replace placeholders with actual values
      if (templateData.variables && typeof templateData.variables === 'object') {
        Object.keys(templateData.variables).forEach(key => {
          const placeholder = `{${key}}`;
          const value = templateData.variables[key] || '';
          // Escape special regex characters in placeholder for safe replacement
          const escapedPlaceholder = placeholder.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
          formattedContent = formattedContent.replace(new RegExp(escapedPlaceholder, 'g'), value);
        });
      }
      
      return {
        status: "success",
        formatted_prompt: formattedContent,
        variables_used: templateData.variables || {}
      };
    } catch (error) {
      throw new Error(`Template formatting error: ${error}`);
    }
  }

  static async getPromptVersionHistory(templateId: string) {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/admin/prompts/${templateId}/versions`, {
      method: 'GET',
      headers,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  static async restorePromptVersion(templateId: string, versionNumber: number) {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/admin/prompts/${templateId}/restore/${versionNumber}`, {
      method: 'POST',
      headers,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  static async duplicatePromptTemplate(templateId: string, newName: string) {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseURL}/api/admin/prompts/${templateId}/duplicate`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ new_name: newName })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }
}// Export default instance for easier imports
export const api = {
  get: async (endpoint: string) => {
    const headers = await ApiService.getAuthHeaders();
    const response = await fetch(`${ApiService['baseURL']}/api${endpoint}`, {
      headers,
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw { response: { status: response.status, data: errorData } };
    }

    return { data: await response.json() };
  },

  post: async (endpoint: string, data?: any) => {
    const headers = await ApiService.getAuthHeaders();
    const response = await fetch(`${ApiService['baseURL']}/api${endpoint}`, {
      method: 'POST',
      headers,
      body: data ? JSON.stringify(data) : undefined,
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw { response: { status: response.status, data: errorData } };
    }

    return { data: await response.json() };
  },

  put: async (endpoint: string, data?: any) => {
    const headers = await ApiService.getAuthHeaders();
    const response = await fetch(`${ApiService['baseURL']}/api${endpoint}`, {
      method: 'PUT',
      headers,
      body: data ? JSON.stringify(data) : undefined,
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw { response: { status: response.status, data: errorData } };
    }

    return { data: await response.json() };
  },

  delete: async (endpoint: string) => {
    const headers = await ApiService.getAuthHeaders();
    const response = await fetch(`${ApiService['baseURL']}/api${endpoint}`, {
      method: 'DELETE',
      headers,
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw { response: { status: response.status, data: errorData } };
    }

    return { data: await response.json() };
  }
};