import logging
from typing import List, Dict, Optional, Tuple
import asyncpg
import numpy as np
from config.settings import settings
from config.supabase_client import supabase

logger = logging.getLogger(__name__)

class VectorStore:
    """Service for managing document embeddings in Supabase pgvector."""
    
    def __init__(self):
        """Initialize vector store connection."""
        self.dimension = 768  # Gemini embedding dimension
        self.table_name = "document_embeddings"
        
    async def create_tables(self):
        """Create necessary tables and indexes for vector storage."""
        try:
            # Connect to database
            conn = await asyncpg.connect(settings.database_url)
            
            # Enable pgvector extension
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            
            # Create documents table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL,
                    filename VARCHAR(255) NOT NULL,
                    file_type VARCHAR(10) NOT NULL,
                    content TEXT NOT NULL,
                    character_count INTEGER NOT NULL,
                    word_count INTEGER NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)
            
            # Create document embeddings table
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                    chunk_text TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    embedding vector({self.dimension}) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)
            
            # Create indexes for better performance
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_document_embeddings_document_id 
                ON {self.table_name}(document_id);
            """)
            
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_document_embeddings_embedding 
                ON {self.table_name} USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100);
            """)
            
            await conn.close()
            logger.info("Vector store tables created successfully")
            
        except Exception as e:
            logger.error(f"Error creating vector store tables: {str(e)}")
            raise Exception(f"Failed to create vector store tables: {str(e)}")
    
    async def store_document(self, user_id: str, document_data: Dict, chunks: List[str], embeddings: List[List[float]]) -> str:
        """
        Store document and its embeddings.
        
        Args:
            user_id: User ID
            document_data: Document metadata
            chunks: Text chunks
            embeddings: Corresponding embeddings
            
        Returns:
            Document ID
        """
        try:
            conn = await asyncpg.connect(settings.database_url)
            
            # Start transaction
            async with conn.transaction():
                # Insert document
                document_id = await conn.fetchval("""
                    INSERT INTO documents (user_id, filename, file_type, content, character_count, word_count, size_bytes)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING id
                """, user_id, document_data['filename'], document_data['file_type'], 
                document_data['text_content'], document_data['character_count'], 
                document_data['word_count'], document_data['size_bytes'])
                
                # Insert embeddings
                for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                    await conn.execute(f"""
                        INSERT INTO {self.table_name} (document_id, chunk_text, chunk_index, embedding)
                        VALUES ($1, $2, $3, $4)
                    """, document_id, chunk, i, embedding)
            
            await conn.close()
            logger.info(f"Document stored successfully with ID: {document_id}")
            return str(document_id)
            
        except Exception as e:
            logger.error(f"Error storing document: {str(e)}")
            raise Exception(f"Failed to store document: {str(e)}")
    
    async def similarity_search(self, query_embedding: List[float], user_id: str, limit: int = 5) -> List[Dict]:
        """
        Perform similarity search for relevant chunks.
        
        Args:
            query_embedding: Query embedding vector
            user_id: User ID to filter documents
            limit: Number of results to return
            
        Returns:
            List of similar chunks with metadata
        """
        try:
            conn = await asyncpg.connect(settings.database_url)
            
            # Perform similarity search
            results = await conn.fetch(f"""
                SELECT 
                    de.chunk_text,
                    de.chunk_index,
                    d.filename,
                    d.file_type,
                    de.embedding <=> $1 as distance,
                    1 - (de.embedding <=> $1) as similarity_score
                FROM {self.table_name} de
                JOIN documents d ON de.document_id = d.id
                WHERE d.user_id = $2
                ORDER BY de.embedding <=> $1
                LIMIT $3
            """, query_embedding, user_id, limit)
            
            await conn.close()
            
            # Convert results to list of dictionaries
            similar_chunks = []
            for row in results:
                similar_chunks.append({
                    'chunk_text': row['chunk_text'],
                    'chunk_index': row['chunk_index'],
                    'filename': row['filename'],
                    'file_type': row['file_type'],
                    'distance': float(row['distance']),
                    'similarity_score': float(row['similarity_score'])
                })
            
            logger.info(f"Found {len(similar_chunks)} similar chunks")
            return similar_chunks
            
        except Exception as e:
            logger.error(f"Error performing similarity search: {str(e)}")
            raise Exception(f"Failed to perform similarity search: {str(e)}")
    
    async def delete_document(self, document_id: str, user_id: str) -> bool:
        """
        Delete a document and its embeddings.
        
        Args:
            document_id: Document ID to delete
            user_id: User ID for authorization
            
        Returns:
            Success status
        """
        try:
            conn = await asyncpg.connect(settings.database_url)
            
            # Delete document (embeddings will be deleted by CASCADE)
            result = await conn.execute("""
                DELETE FROM documents 
                WHERE id = $1 AND user_id = $2
            """, document_id, user_id)
            
            await conn.close()
            
            # Check if document was deleted
            rows_affected = int(result.split()[-1])
            success = rows_affected > 0
            
            if success:
                logger.info(f"Document {document_id} deleted successfully")
            else:
                logger.warning(f"Document {document_id} not found or unauthorized")
            
            return success
            
        except Exception as e:
            logger.error(f"Error deleting document: {str(e)}")
            raise Exception(f"Failed to delete document: {str(e)}")
    
    async def get_user_documents(self, user_id: str) -> List[Dict]:
        """Get all documents for a user."""
        try:
            conn = await asyncpg.connect(settings.database_url)
            
            results = await conn.fetch("""
                SELECT id, filename, file_type, character_count, word_count, size_bytes, created_at
                FROM documents
                WHERE user_id = $1
                ORDER BY created_at DESC
            """, user_id)
            
            await conn.close()
            
            documents = []
            for row in results:
                documents.append({
                    'id': str(row['id']),
                    'filename': row['filename'],
                    'file_type': row['file_type'],
                    'character_count': row['character_count'],
                    'word_count': row['word_count'],
                    'size_bytes': row['size_bytes'],
                    'created_at': row['created_at'].isoformat()
                })
            
            return documents
            
        except Exception as e:
            logger.error(f"Error fetching user documents: {str(e)}")
            raise Exception(f"Failed to fetch user documents: {str(e)}")

# Global instance
vector_store = VectorStore()