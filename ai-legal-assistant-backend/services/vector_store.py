import logging
from typing import List, Dict, Optional, Tuple
import asyncpg
import json
from datetime import datetime
from config.settings import settings
from config.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

class VectorStore:
    """Enhanced vector store for document chunks and embeddings with hybrid search support."""
    
    def __init__(self):
        """Initialize vector store connection."""
        self.dimension = 768  # Gemini embedding dimension
        self.supabase = get_supabase_client()
    
    async def store_processed_document(self, user_id: str, document_data: Dict, 
                                     chunks_with_embeddings: List[Dict], 
                                     session_id: str = None) -> str:
        """
        Store document and all its processed chunks with embeddings.
        
        Args:
            user_id: User ID
            document_data: Document metadata
            chunks_with_embeddings: List of chunks with embeddings
            session_id: Optional chat session ID
            
        Returns:
            Document ID
        """
        try:
            # First, store the document
            document_result = self.supabase.table('documents').insert({
                'user_id': user_id,
                'title': document_data['filename'],
                'file_name': document_data['filename'],
                'file_size': document_data.get('size_bytes', 0),
                'file_type': document_data['file_type'].replace('.', ''),
                'processing_status': 'processing',
                'is_public': False,  # User documents are private by default
                'uploaded_by_admin': False,
                'chat_session_id': session_id,
                'metadata': {
                    'character_count': document_data.get('character_count', 0),
                    'word_count': document_data.get('word_count', 0),
                    'total_chunks': len(chunks_with_embeddings)
                }
            }).execute()
            
            if not document_result.data:
                raise Exception("Failed to store document")
            
            document_id = document_result.data[0]['id']
            
            # Store all chunks with embeddings
            await self._store_document_chunks(document_id, chunks_with_embeddings)
            
            # Update document status to completed
            self.supabase.table('documents').update({
                'processing_status': 'completed'
            }).eq('id', document_id).execute()
            
            logger.info(f"Stored document {document_id} with {len(chunks_with_embeddings)} chunks")
            return document_id
            
        except Exception as e:
            logger.error(f"Error storing processed document: {str(e)}")
            raise Exception(f"Failed to store processed document: {str(e)}")
    
    async def store_admin_document(self, admin_user_id: str, document_data: Dict, 
                                  chunks_with_embeddings: List[Dict], 
                                  category: str = None) -> str:
        """
        Store admin document as public knowledge base entry.
        
        Args:
            admin_user_id: Admin user ID
            document_data: Document metadata
            chunks_with_embeddings: List of chunks with embeddings
            category: Document category (e.g., 'traffic_law', 'criminal_law')
            
        Returns:
            Document ID
        """
        try:
            # Store document as public
            document_result = self.supabase.table('documents').insert({
                'user_id': admin_user_id,
                'admin_user_id': admin_user_id,
                'title': document_data['filename'],
                'file_name': document_data['filename'],
                'file_size': document_data.get('size_bytes', 0),
                'file_type': document_data['file_type'].replace('.', ''),
                'processing_status': 'processing',
                'is_public': True,  # Admin documents are public
                'uploaded_by_admin': True,
                'document_category': category,
                'is_active': True,
                'metadata': {
                    'character_count': document_data.get('character_count', 0),
                    'word_count': document_data.get('word_count', 0),
                    'total_chunks': len(chunks_with_embeddings),
                    'admin_uploaded': True,
                    'category': category
                }
            }).execute()
            
            if not document_result.data:
                raise Exception("Failed to store admin document")
            
            document_id = document_result.data[0]['id']
            
            # Store all chunks with embeddings
            await self._store_document_chunks(document_id, chunks_with_embeddings)
            
            # Update document status to completed
            self.supabase.table('documents').update({
                'processing_status': 'completed'
            }).eq('id', document_id).execute()
            
            logger.info(f"Stored admin document {document_id} with {len(chunks_with_embeddings)} chunks")
            return document_id
            
        except Exception as e:
            logger.error(f"Error storing admin document: {str(e)}")
            raise Exception(f"Failed to store admin document: {str(e)}")

    async def _store_document_chunks(self, document_id: str, chunks: List[Dict]):
        """Store document chunks with embeddings in batch."""
        try:
            chunk_records = []
            
            for chunk in chunks:
                chunk_record = {
                    'document_id': document_id,
                    'chunk_content': chunk['chunk_text'],
                    'chunk_index': chunk['chunk_index'],
                    'embedding': chunk['embedding'],
                    'token_count': chunk['token_count'],
                    'page_number': chunk.get('page_number'),
                    'chapter_title': chunk.get('chapter_title'),
                    'section_title': chunk.get('section_title'),
                    'metadata': {
                        'character_count': chunk['character_count'],
                        'word_count': chunk['word_count'],
                        'keywords': chunk.get('keywords', []),
                        'document_metadata': chunk.get('document_metadata', {}),
                        'embedding_model': chunk.get('embedding_model'),
                        'embedding_dimensions': chunk.get('embedding_dimensions')
                    }
                }
                chunk_records.append(chunk_record)
            
            # Batch insert chunks
            batch_size = 50
            for i in range(0, len(chunk_records), batch_size):
                batch = chunk_records[i:i + batch_size]
                result = self.supabase.table('document_chunks').insert(batch).execute()
                
                if not result.data:
                    raise Exception(f"Failed to insert chunk batch {i//batch_size + 1}")
            
            logger.info(f"Stored {len(chunk_records)} chunks for document {document_id}")
            
        except Exception as e:
            logger.error(f"Error storing document chunks: {str(e)}")
            raise Exception(f"Failed to store document chunks: {str(e)}")
    
    async def hybrid_similarity_search(self, query_embedding: List[float], 
                                     user_id: str,
                                     include_public: bool = True,
                                     include_user_docs: bool = True,
                                     session_id: str = None,
                                     document_categories: List[str] = None,
                                     limit: int = 10,
                                     similarity_threshold: float = 0.7) -> Dict:
        """
        Search across both user documents and public knowledge base.
        
        Args:
            query_embedding: Query embedding vector
            user_id: User ID for filtering user documents
            include_public: Whether to search public documents
            include_user_docs: Whether to search user documents
            session_id: Optional session ID for session-specific documents
            document_categories: Filter by document categories
            limit: Maximum number of results per source
            similarity_threshold: Minimum similarity score
            
        Returns:
            Dict with categorized search results
        """
        try:
            results = {
                'public_results': [],
                'user_results': [],
                'session_results': []
            }
            
            # Search public documents
            if include_public:
                results['public_results'] = await self.search_public_documents(
                    query_embedding, limit//2, similarity_threshold
                )
            
            # Search user documents
            if include_user_docs:
                results['user_results'] = await self.search_user_documents(
                    query_embedding, user_id, limit//2, similarity_threshold
                )
            
            # Search session-specific documents
            if session_id:
                results['session_results'] = await self.search_session_documents(
                    query_embedding, session_id, limit//3, similarity_threshold
                )
            
            return results
            
        except Exception as e:
            logger.error(f"Error in hybrid similarity search: {str(e)}")
            raise Exception(f"Failed to perform hybrid similarity search: {str(e)}")

    async def search_public_documents(self, query_embedding: List[float], limit: int = 5) -> List[Dict]:
        """Search public documents (common knowledge base)"""
        try:
            # Convert embedding to string format for pgvector
            embedding_str = str(query_embedding)
            
            # Search using RPC function for vector similarity
            result = self.supabase.rpc('search_public_documents', {
                'query_embedding': embedding_str,
                'match_threshold': 0.7,
                'match_count': limit
            }).execute()
            
            if result.data:
                return result.data
            
            # Fallback to regular query if RPC doesn't exist
            result = self.supabase.table('document_chunks').select(
                'id, document_id, chunk_content, chunk_index, page_number, '
                'chapter_title, section_title, metadata, '
                'documents!inner(id, title, file_name, document_category, is_public, is_active)'
            ).eq('documents.is_public', True).eq('documents.is_active', True).limit(limit).execute()
            
            # Add similarity scores (would be calculated by RPC in production)
            chunks = []
            for chunk in result.data or []:
                chunks.append({
                    'id': chunk['id'],
                    'document_id': chunk['document_id'],
                    'chunk_content': chunk['chunk_content'],
                    'chunk_index': chunk['chunk_index'],
                    'page_number': chunk['page_number'],
                    'chapter_title': chunk['chapter_title'],
                    'section_title': chunk['section_title'],
                    'metadata': chunk['metadata'],
                    'document_title': chunk['documents']['title'],
                    'document_category': chunk['documents']['document_category'],
                    'similarity': 0.8,  # Default similarity score
                    'source_type': 'public'
                })
            
            logger.info(f"Found {len(chunks)} public document chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"vector Error searching public documents: {str(e)}")
            return []

    async def search_user_documents(self, query_embedding: List[float], user_id: str, limit: int = 5) -> List[Dict]:
        """Search user's private documents"""
        try:
            # Convert embedding to string format for pgvector
            embedding_str = str(query_embedding)
            
            # Search using RPC function for vector similarity
            result = self.supabase.rpc('search_user_documents', {
                'query_embedding': embedding_str,
                'user_id': user_id,
                'match_threshold': 0.7,
                'match_count': limit
            }).execute()
            
            if result.data:
                return result.data
            
            # Fallback to regular query if RPC doesn't exist
            result = self.supabase.table('document_chunks').select(
                'id, document_id, chunk_content, chunk_index, page_number, '
                'chapter_title, section_title, metadata, '
                'documents!inner(id, title, file_name, user_id, is_public)'
            ).eq('documents.user_id', user_id).eq('documents.is_public', False).limit(limit).execute()
            
            # Add similarity scores
            chunks = []
            for chunk in result.data or []:
                chunks.append({
                    'id': chunk['id'],
                    'document_id': chunk['document_id'],
                    'chunk_content': chunk['chunk_content'],
                    'chunk_index': chunk['chunk_index'],
                    'page_number': chunk['page_number'],
                    'chapter_title': chunk['chapter_title'],
                    'section_title': chunk['section_title'],
                    'metadata': chunk['metadata'],
                    'document_title': chunk['documents']['title'],
                    'similarity': 0.8,  # Default similarity score
                    'source_type': 'user'
                })
            
            logger.info(f"Found {len(chunks)} user document chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"Error searching user documents: {str(e)}")
            return []

    async def search_session_documents(self, query_embedding: List[float], session_id: str, limit: int = 5) -> List[Dict]:
        """Search documents uploaded in current session"""
        try:
            # Convert embedding to string format for pgvector
            embedding_str = str(query_embedding)
            
            # Search using RPC function for vector similarity
            result = self.supabase.rpc('search_session_documents', {
                'query_embedding': embedding_str,
                'session_id': session_id,
                'match_threshold': 0.7,
                'match_count': limit
            }).execute()
            
            if result.data:
                return result.data
            
            # Fallback to regular query if RPC doesn't exist
            result = self.supabase.table('document_chunks').select(
                'id, document_id, chunk_content, chunk_index, page_number, '
                'chapter_title, section_title, metadata, '
                'documents!inner(id, title, file_name, chat_session_id)'
            ).eq('documents.chat_session_id', session_id).limit(limit).execute()
            
            # Add similarity scores
            chunks = []
            for chunk in result.data or []:
                chunks.append({
                    'id': chunk['id'],
                    'document_id': chunk['document_id'],
                    'chunk_content': chunk['chunk_content'],
                    'chunk_index': chunk['chunk_index'],
                    'page_number': chunk['page_number'],
                    'chapter_title': chunk['chapter_title'],
                    'section_title': chunk['section_title'],
                    'metadata': chunk['metadata'],
                    'document_title': chunk['documents']['title'],
                    'similarity': 0.8,  # Default similarity score
                    'source_type': 'session'
                })
            
            logger.info(f"Found {len(chunks)} session document chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"Error searching session documents: {str(e)}")
            return []

    # Legacy method for backward compatibility
    async def similarity_search(self, query_embedding: List[float], 
                              document_id: Optional[str] = None,
                              limit: int = 10,
                              similarity_threshold: float = 0.7) -> List[Dict]:
        """
        Legacy similarity search method for backward compatibility.
        """
        try:
            query_builder = self.supabase.table('document_chunks').select(
                'id, document_id, chunk_content, chunk_index, token_count, '
                'page_number, chapter_title, section_title, metadata'
            )
            
            if document_id:
                query_builder = query_builder.eq('document_id', document_id)
            
            result = query_builder.limit(limit).execute()
            
            if not result.data:
                return []
            
            return result.data
            
        except Exception as e:
            logger.error(f"Error in similarity search: {str(e)}")
            raise Exception(f"Failed to perform similarity search: {str(e)}")
    
    async def get_document_chunks(self, document_id: str) -> List[Dict]:
        """Get all chunks for a specific document."""
        try:
            result = self.supabase.table('document_chunks').select(
                'id, chunk_content, chunk_index, token_count, '
                'page_number, chapter_title, section_title, metadata'
            ).eq('document_id', document_id).order('chunk_index').execute()
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error getting document chunks: {str(e)}")
            return []
    
    async def get_user_documents(self, user_id: str) -> List[Dict]:
        """Get all documents for a user."""
        try:
            result = self.supabase.table('documents').select(
                'id, title, file_name, file_size, file_type, '
                'processing_status, upload_date, metadata, chat_session_id'
            ).eq('user_id', user_id).eq('is_public', False).order('upload_date', desc=True).execute()
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error getting user documents: {str(e)}")
            return []

    async def get_public_documents(self) -> List[Dict]:
        """Get all public documents for admin management"""
        try:
            result = self.supabase.table('documents').select(
                'id, title, file_name, file_size, file_type, document_category, '
                'processing_status, is_active, upload_date, created_at, metadata'
            ).eq('is_public', True).eq('uploaded_by_admin', True).order('created_at', desc=True).execute()
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error getting public documents: {str(e)}")
            return []

    async def get_document_stats(self, document_id: str) -> Dict:
        """Get statistics for a specific document"""
        try:
            # Get document info
            doc_result = self.supabase.table('documents').select('*').eq('id', document_id).execute()
            
            if not doc_result.data:
                return {}
            
            # Get chunk count
            chunk_result = self.supabase.table('document_chunks').select('id', count='exact').eq('document_id', document_id).execute()
            
            document = doc_result.data[0]
            return {
                'document_id': document_id,
                'title': document['title'],
                'file_size': document['file_size'],
                'file_type': document['file_type'],
                'chunk_count': chunk_result.count,
                'processing_status': document['processing_status'],
                'upload_date': document['upload_date'],
                'is_public': document['is_public'],
                'metadata': document['metadata']
            }
            
        except Exception as e:
            logger.error(f"Error getting document stats: {str(e)}")
            return {}