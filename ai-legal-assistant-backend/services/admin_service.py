import logging
from typing import Dict, List
from datetime import datetime
from config.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

class AdminService:
    def __init__(self):
        self.supabase = get_supabase_client()
    
    async def verify_admin_role(self, user_id: str) -> bool:
        """Check if user has admin privileges"""
        try:
            result = self.supabase.table('user_roles').select('role').eq('user_id', user_id).eq('role', 'admin').eq('is_active', True).execute()
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"Error verifying admin role: {str(e)}")
            return False
    
    async def upload_public_document(self, admin_user_id: str, document_data: Dict,
                                   chunks_with_embeddings: List[Dict],
                                   category: str = None) -> str:
        """Upload document to common knowledge base"""
        try:
            # Store document with is_public=True, uploaded_by_admin=True
            document_result = self.supabase.table('documents').insert({
                'user_id': admin_user_id,
                'admin_user_id': admin_user_id,
                'title': document_data['filename'],
                'file_name': document_data['filename'],
                'file_size': document_data.get('size_bytes', 0),
                'file_type': document_data['file_type'].replace('.', ''),
                'processing_status': 'processing',
                'is_public': True,
                'uploaded_by_admin': True,
                'document_category': category,
                'is_active': True,
                'metadata': {
                    'character_count': document_data.get('character_count', 0),
                    'word_count': document_data.get('word_count', 0),
                    'total_chunks': len(chunks_with_embeddings),
                    'upload_source': 'admin'
                }
            }).execute()
            
            if not document_result.data:
                raise Exception("Failed to store admin document")
            
            document_id = document_result.data[0]['id']
            
            # Store chunks with embeddings
            for chunk in chunks_with_embeddings:
                self.supabase.table('document_chunks').insert({
                    'document_id': document_id,
                    'chunk_content': chunk['chunk_text'],
                    'chunk_index': chunk['chunk_index'],
                    'embedding': chunk['embedding'],
                    'page_number': chunk.get('page_number'),
                    'chapter_title': chunk.get('chapter_title'),
                    'section_title': chunk.get('section_title'),
                    'token_count': chunk.get('token_count', 0),
                    'metadata': {
                        **chunk.get('metadata', {}),
                        'document_category': category,
                        'is_public': True
                    }
                }).execute()
            
            # Update document status to completed
            self.supabase.table('documents').update({
                'processing_status': 'completed'
            }).eq('id', document_id).execute()
            
            logger.info(f"Successfully uploaded admin document {document_id} with {len(chunks_with_embeddings)} chunks")
            return document_id
            
        except Exception as e:
            logger.error(f"Error uploading public document: {str(e)}")
            raise Exception(f"Failed to upload public document: {str(e)}")
    
    async def manage_public_documents(self, admin_user_id: str) -> List[Dict]:
        """Get all public documents for admin management"""
        try:
            # Verify admin privileges
            if not await self.verify_admin_role(admin_user_id):
                raise Exception("Admin privileges required")
            
            # Get all public documents
            result = self.supabase.table('documents').select(
                'id, title, file_name, file_size, file_type, document_category, '
                'processing_status, is_active, upload_date, created_at, metadata'
            ).eq('is_public', True).eq('uploaded_by_admin', True).order('created_at', desc=True).execute()
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error managing public documents: {str(e)}")
            raise Exception(f"Failed to retrieve public documents: {str(e)}")
    
    async def activate_deactivate_document(self, admin_user_id: str,
                                         document_id: str, is_active: bool) -> bool:
        """Activate or deactivate public documents"""
        try:
            # Verify admin privileges
            if not await self.verify_admin_role(admin_user_id):
                raise Exception("Admin privileges required")
            
            # Update document status
            result = self.supabase.table('documents').update({
                'is_active': is_active
            }).eq('id', document_id).eq('is_public', True).eq('uploaded_by_admin', True).execute()
            
            if not result.data:
                raise Exception("Document not found or not authorized")
            
            logger.info(f"Document {document_id} {'activated' if is_active else 'deactivated'}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating document status: {str(e)}")
            raise Exception(f"Failed to update document status: {str(e)}")
    
    async def get_admin_statistics(self, admin_user_id: str) -> Dict:
        """Get admin dashboard statistics"""
        try:
            # Verify admin privileges
            if not await self.verify_admin_role(admin_user_id):
                raise Exception("Admin privileges required")
            
            # Get document counts
            public_docs = self.supabase.table('documents').select('id', count='exact').eq('is_public', True).eq('is_active', True).execute()
            total_docs = self.supabase.table('documents').select('id', count='exact').execute()
            
            # Get user count
            users = self.supabase.table('user_roles').select('user_id', count='exact').eq('role', 'user').eq('is_active', True).execute()
            
            # Get recent activity
            recent_uploads = self.supabase.table('documents').select('*').eq('is_public', True).order('created_at', desc=True).limit(5).execute()
            
            return {
                'public_documents': public_docs.count,
                'total_documents': total_docs.count,
                'active_users': users.count,
                'recent_uploads': recent_uploads.data or []
            }
            
        except Exception as e:
            logger.error(f"Error getting admin statistics: {str(e)}")
            raise Exception(f"Failed to get admin statistics: {str(e)}")
    
    async def delete_public_document(self, admin_user_id: str, document_id: str) -> bool:
        """Delete a public document and all its chunks"""
        try:
            # Verify admin privileges
            if not await self.verify_admin_role(admin_user_id):
                raise Exception("Admin privileges required")
            
            # Delete document chunks first
            self.supabase.table('document_chunks').delete().eq('document_id', document_id).execute()
            
            # Delete document
            result = self.supabase.table('documents').delete().eq('id', document_id).eq('is_public', True).eq('uploaded_by_admin', True).execute()
            
            if not result.data:
                raise Exception("Document not found or not authorized")
            
            logger.info(f"Successfully deleted public document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting public document: {str(e)}")
            raise Exception(f"Failed to delete public document: {str(e)}")
    
    async def grant_admin_role(self, admin_user_id: str, target_user_id: str) -> bool:
        """Grant admin role to a user"""
        try:
            # Verify admin privileges
            if not await self.verify_admin_role(admin_user_id):
                raise Exception("Admin privileges required")
            
            # Check if user already has admin role
            existing = self.supabase.table('user_roles').select('id').eq('user_id', target_user_id).eq('role', 'admin').eq('is_active', True).execute()
            
            if existing.data:
                return True  # Already has admin role
            
            # Grant admin role
            result = self.supabase.table('user_roles').insert({
                'user_id': target_user_id,
                'role': 'admin',
                'granted_by': admin_user_id,
                'granted_at': datetime.now().isoformat(),
                'is_active': True
            }).execute()
            
            if not result.data:
                raise Exception("Failed to grant admin role")
            
            logger.info(f"Admin role granted to user {target_user_id} by {admin_user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error granting admin role: {str(e)}")
            raise Exception(f"Failed to grant admin role: {str(e)}")
    
    async def revoke_admin_role(self, admin_user_id: str, target_user_id: str) -> bool:
        """Revoke admin role from a user"""
        try:
            # Verify admin privileges
            if not await self.verify_admin_role(admin_user_id):
                raise Exception("Admin privileges required")
            
            # Can't revoke own admin role
            if admin_user_id == target_user_id:
                raise Exception("Cannot revoke your own admin role")
            
            # Revoke admin role
            result = self.supabase.table('user_roles').update({
                'is_active': False
            }).eq('user_id', target_user_id).eq('role', 'admin').execute()
            
            if not result.data:
                raise Exception("Admin role not found for user")
            
            logger.info(f"Admin role revoked from user {target_user_id} by {admin_user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error revoking admin role: {str(e)}")
            raise Exception(f"Failed to revoke admin role: {str(e)}")