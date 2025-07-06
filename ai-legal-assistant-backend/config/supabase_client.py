import os
from supabase import create_client, Client
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class SupabaseClient:
    """Supabase client wrapper for database operations."""
    
    def __init__(self):
        """Initialize Supabase client with service role key for backend operations."""
        try:
            self.url = settings.supabase_url
            self.key = settings.supabase_key  # This should be the service role key
            
            # Create client with service role key for admin operations
            self.client: Client = create_client(self.url, self.key)
            
            logger.info("Supabase client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {str(e)}")
            raise Exception(f"Supabase initialization failed: {str(e)}")
    
    def get_client(self) -> Client:
        """Get the Supabase client instance."""
        return self.client
    
    async def test_connection(self) -> bool:
        """Test the database connection."""
        try:
            # Test with a simple query
            result = self.client.table('documents').select('count').limit(1).execute()
            logger.info("Supabase connection test successful")
            return True
        except Exception as e:
            logger.error(f"Supabase connection test failed: {str(e)}")
            return False
    
    async def execute_sql(self, query: str):
        """Execute raw SQL query (for setup operations)."""
        try:
            result = self.client.rpc('execute_sql', {'query': query}).execute()
            return result
        except Exception as e:
            logger.error(f"SQL execution failed: {str(e)}")
            raise Exception(f"Failed to execute SQL: {str(e)}")

# Global Supabase client instance
supabase_client = SupabaseClient()
supabase = supabase_client.get_client()

# For backward compatibility and easy imports
def get_supabase_client() -> Client:
    """Get the global Supabase client instance."""
    return supabase