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