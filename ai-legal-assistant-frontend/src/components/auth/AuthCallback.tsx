// src/components/auth/AuthCallback.tsx
import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppDispatch } from '../../app/hooks';
import { supabase } from '../../lib/supabase';
import { setUser } from '../../features/auth/authSlice';

const AuthCallback = () => {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  
  useEffect(() => {
    console.log("Auth callback handling");
    
    const getSession = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      console.log("Session check:", session ? "Session exists" : "No session");
      
      if (session) {
        dispatch(setUser({
          id: session.user.id,
          email: session.user.email,
          avatar_url: session.user.user_metadata?.avatar_url,
          user_metadata: session.user.user_metadata
        }));
        navigate('/dashboard');
      } else {
        navigate('/login');
      }
    };
    
    getSession();
  }, [dispatch, navigate]);
  
  return <div>Completing sign in...</div>;
};

export default AuthCallback;