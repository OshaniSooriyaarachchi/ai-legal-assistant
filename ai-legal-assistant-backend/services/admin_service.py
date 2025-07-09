class AdminService:
    def __init__(self):
        self.supabase = get_supabase_client()
    
    async def verify_admin_role(self, user_id: str) -> bool:
        """Check if user has admin privileges"""
        result = self.supabase.table('user_roles').select('role').eq('user_id', user_id).eq('role', 'admin').eq('is_active', True).execute()
        return len(result.data) > 0
    
    async def upload_public_document(self, admin_user_id: str, document_data: Dict,
                                   chunks_with_embeddings: List[Dict],
                                   category: str = None) -> str:
        """Upload document to common knowledge base"""
        # Store document with is_public=True, uploaded_by_admin=True
        pass
    
    async def manage_public_documents(self, admin_user_id: str) -> List[Dict]:
        """Get all public documents for admin management"""
        pass
    
    async def activate_deactivate_document(self, admin_user_id: str,
                                         document_id: str, is_active: bool) -> bool:
        """Activate or deactivate public documents"""
        pass