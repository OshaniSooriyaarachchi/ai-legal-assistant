import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppDispatch } from '../../app/hooks';
import { supabase } from '../../lib/supabase';
import { setUser } from '../../features/auth/authSlice';

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
        
        if (!window.location.pathname.includes('/dashboard')) {
          navigate('/dashboard');
        }
      } else if (event === 'SIGNED_OUT') {
        dispatch({ type: 'auth/signOut' });
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