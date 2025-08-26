import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppDispatch } from '../../app/hooks';
import { supabase } from '../../lib/supabase';
import { setUser } from '../../features/auth/authSlice';
import { loadChatSessions, clearChatLocal } from '../../features/chat/chatSlice';

const AuthListener: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();

  useEffect(() => {
    // Check for existing session on component mount
    const checkSession = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      
      if (session) {
        dispatch(setUser({
          id: session.user.id,
          email: session.user.email,
          avatar_url: session.user.user_metadata?.avatar_url || 
                     session.user.user_metadata?.picture, // Facebook provides 'picture'
          user_metadata: {
            full_name: session.user.user_metadata?.full_name || 
                      session.user.user_metadata?.name // Facebook provides 'name'
          }
        }));
        
        // Load chat sessions for existing session
        try {
          dispatch(loadChatSessions());
        } catch (error) {
          console.error('Failed to load chat sessions on session check:', error);
        }
        
        // Only redirect if user is on login/signup pages, not if they're on dashboard or admin
        if (window.location.pathname === '/login' || 
            window.location.pathname === '/signup' || 
            window.location.pathname === '/' ||
            window.location.pathname === '/forgot-password' ||
            window.location.pathname === '/reset-password') {
          navigate('/dashboard');
        }
      }
    };

    checkSession();

    // Listen for auth state changes
    const { data: authListener } = supabase.auth.onAuthStateChange((event, session) => {
      console.log("Auth state changed:", event);
      
      if (event === 'SIGNED_IN' && session) {
        dispatch(setUser({
          id: session.user.id,
          email: session.user.email,
          avatar_url: session.user.user_metadata?.avatar_url ||
                     session.user.user_metadata?.picture,
          user_metadata: {
            full_name: session.user.user_metadata?.full_name ||
                      session.user.user_metadata?.name
          }
        }));
        
        // Load chat sessions on sign in
        try {
          dispatch(loadChatSessions());
        } catch (error) {
          console.error('Failed to load chat sessions on login:', error);
        }
        
        if (!window.location.pathname.includes('/dashboard') && !window.location.pathname.includes('/admin')) {
          navigate('/dashboard');
        }
      } else if (event === 'SIGNED_OUT') {
        dispatch({ type: 'auth/signOut' });
        dispatch(clearChatLocal()); // Clear chat sessions and messages
        navigate('/login');
      }
    });

    return () => {
      authListener.subscription.unsubscribe();
    };
  }, [dispatch, navigate]);

  return <>{children}</>;
};

export default AuthListener;