// Follow this setup guide to integrate the Deno language server with your editor:
// https://deno.land/manual/getting_started/setup_your_environment
// This enables autocomplete, go to definition, etc.

// Setup type definitions for built-in Supabase Runtime APIs
import "jsr:@supabase/functions-js/edge-runtime.d.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

console.log("Facebook Data Deletion Function loaded!")

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Content-Type': 'application/json',
};

Deno.serve(async (req) => {
  // Handle CORS preflight requests
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }
  
  try {
    // Facebook verification - they'll make a GET request first
    if (req.method === 'GET') {
      console.log('GET request received - Facebook verification');
      return new Response(
        JSON.stringify({ confirmation_code: "verify_" + Math.random().toString(36).substring(2, 10) }),
        { headers: corsHeaders, status: 200 }
      );
    }
    
    // Data deletion request - this will be a POST
    if (req.method === 'POST') {
      console.log('Received deletion request');
      let userId: string | null = null;
      
      try {
        const body = await req.json();
        console.log('Request body:', body);
        
        // In production, you would:
        // 1. Parse and verify the signed_request from Facebook
        // 2. Extract the user ID
        // 3. Delete user data from your database
        
        // Example of how to initialize Supabase client (uncomment when needed):
        // const supabase = createClient(
        //   Deno.env.get('SUPABASE_URL') ?? '',
        //   Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
        // );
        
        // Example deletion logic (uncomment and modify when ready):
        // if (userId) {
        //   await supabase
        //     .from('profiles')
        //     .delete()
        //     .eq('id', userId);
        // }
        
        // For now, just log and return a success response
        userId = 'example-user-id'; // In production, extract this from the signed_request
      } catch (e) {
        console.error('Error parsing request body:', e);
      }
      
      // Return success response to Facebook
      return new Response(
        JSON.stringify({ confirmation_code: "delete_" + Math.random().toString(36).substring(2, 10) }),
        { headers: corsHeaders, status: 200 }
      );
    }
    
    // Invalid method
    return new Response(
      JSON.stringify({ error: 'Method not allowed' }),
      { headers: corsHeaders, status: 405 }
    );
  } catch (error) {
    console.error('Error processing request:', error);
    return new Response(
      JSON.stringify({ error: error.message }),
      { headers: corsHeaders, status: 500 }
    );
  }
})

/* To invoke locally:

  1. Run `supabase start` (see: https://supabase.com/docs/reference/cli/supabase-start)
  2. Make an HTTP request:

  curl -i --location --request POST 'http://127.0.0.1:54321/functions/v1/user-data-deletion' \
    --header 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0' \
    --header 'Content-Type: application/json' \
    --data '{"signed_request":"facebook_signed_request_here"}'

*/
