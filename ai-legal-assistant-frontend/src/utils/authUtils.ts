// src/utils/authUtils.ts
import { supabase } from '../lib/supabase';

export const checkEmailExists = async (email: string): Promise<boolean> => {
  try {
    // Try to sign in with an incorrect password
    // This is a lightweight way to check if the email exists
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password: 'check_email_exists_only', // Deliberately incorrect password
    });

    // If error message indicates invalid credentials (not user not found),
    // the email exists
    return error?.message?.includes('Invalid login credentials') || false;
  } catch (error) {
    console.error('Error checking email existence:', error);
    return false;
  }
};



export const checkAdminRole = async (supabase: any): Promise<boolean> => {
  try {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) return false;
    
    const { data, error } = await supabase
      .from('user_roles')
      .select('role')
      .eq('user_id', user.id)
      .eq('role', 'admin')
      .eq('is_active', true);

      if (error) {
        console.error('Error checking admin role:', error);
        return false;
      }
    
    return data && data.length > 0;
  } catch (error) {
    console.error('Error checking admin role:', error);
    return false;
  }
};