export interface User {
  id: string;
  email?: string;
  avatar_url?: string;
  user_metadata?: {
    full_name?: string;
  };
}

export interface AuthState {
  user: User | null;
  isLoading: boolean;
  error: string | null;
  isAuthenticated: boolean;
}