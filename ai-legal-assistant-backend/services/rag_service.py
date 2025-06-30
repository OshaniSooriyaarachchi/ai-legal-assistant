import logging
from typing import List, Dict, Optional
import google.generativeai as genai
from services.embedding_service import embedding_service
from services.vector_store import vector_store
from utils.text_chunker import text_chunker
from utils.prompt_templates import PromptTemplates
from config.settings import settings

logger = logging.getLogger(__name__)

class RAGService:
    """Retrieval-Augmented Generation service for legal document assistance."""
    
    def __init__(self):
        """Initialize RAG service."""
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        self.prompt_templates = PromptTemplates()
        
    async def process_document(self, user_id: str, document_data: Dict) -> str:
        """
        Process and store a document for RAG.
        
        Args:
            user_id: User ID
            document_data: Document content and metadata
            
        Returns:
            Document ID
        """
        try:
            # Extract text content
            text_content = document_data['text_content']
            
            # Chunk the text
            chunks = text_chunker.chunk_text(
                text_content,
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap
            )
            
            logger.info(f"Created {len(chunks)} chunks from document")
            
            # Generate embeddings for chunks
            embeddings = await embedding_service.generate_embeddings_batch(chunks)
            
            # Store in vector database
            document_id = await vector_store.store_document(
                user_id=user_id,
                document_data=document_data,
                chunks=chunks,
                embeddings=embeddings
            )
            
            logger.info(f"Document processed and stored with ID: {document_id}")
            return document_id
            
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            raise Exception(f"Failed to process document: {str(e)}")
    
    async def generate_response(self, query: str, user_id: str, conversation_history: Optional[List[Dict]] = None) -> Dict:
        """
        Generate a response to a legal query using RAG.
        
        Args:
            query: User query
            user_id: User ID for document access
            conversation_history: Previous conversation context
            
        Returns:
            Generated response with sources
        """
        try:
            # Generate query embedding
            query_embedding = await embedding_service.generate_query_embedding(query)
            
            # Retrieve relevant chunks
            relevant_chunks = await vector_store.similarity_search(
                query_embedding=query_embedding,
                user_id=user_id,
                limit=settings.top_k
            )
            
            # Build context from relevant chunks
            context = self._build_context(relevant_chunks)
            
            # Generate response using Gemini
            response = await self._generate_with_context(
                query=query,
                context=context,
                conversation_history=conversation_history
            )
            
            # Prepare response with sources
            return {
                'response': response,
                'sources': self._format_sources(relevant_chunks),
                'context_used': len(relevant_chunks) > 0
            }
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise Exception(f"Failed to generate response: {str(e)}")
    
    async def _generate_with_context(self, query: str, context: str, conversation_history: Optional[List[Dict]] = None) -> str:
        """Generate response using Gemini with context."""
        try:
            # Build conversation context
            conversation_context = ""
            if conversation_history:
                conversation_context = self._build_conversation_context(conversation_history)
            
            # Create prompt
            prompt = self.prompt_templates.create_rag_prompt(
                query=query,
                context=context,
                conversation_history=conversation_context
            )
            
            # Generate response
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=settings.temperature,
                    max_output_tokens=2048,
                )
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Error generating with context: {str(e)}")
            return "I apologize, but I'm unable to generate a response at the moment. Please try again."
    
    def _build_context(self, relevant_chunks: List[Dict]) -> str:
        """Build context string from relevant chunks."""
        if not relevant_chunks:
            return "No relevant context found in your documents."
        
        context_parts = []
        for i, chunk in enumerate(relevant_chunks, 1):
            similarity_score = chunk.get('similarity_score', 0)
            context_parts.append(
                f"[Source {i}: {chunk['filename']} (Relevance: {similarity_score:.2f})]\n"
                f"{chunk['chunk_text']}\n"
            )
        
        return "\n".join(context_parts)
    
    def _build_conversation_context(self, conversation_history: List[Dict]) -> str:
        """Build conversation context from history."""
        context_parts = []
        
        # Take last few exchanges to avoid token limits
        recent_history = conversation_history[-6:]  # Last 3 exchanges (user + assistant)
        
        for entry in recent_history:
            role = entry.get('role', 'user')
            content = entry.get('content', '')
            context_parts.append(f"{role.title()}: {content}")
        
        return "\n".join(context_parts)
    
    def _format_sources(self, relevant_chunks: List[Dict]) -> List[Dict]:
        """Format source information for response."""
        sources = []
        seen_files = set()
        
        for chunk in relevant_chunks:
            filename = chunk['filename']
            if filename not in seen_files:
                sources.append({
                    'filename': filename,
                    'file_type': chunk['file_type'],
                    'similarity_score': chunk['similarity_score'],
                    'chunk_preview': chunk['chunk_text'][:200] + "..." if len(chunk['chunk_text']) > 200 else chunk['chunk_text']
                })
                seen_files.add(filename)
        
        return sources
    
    async def get_document_summary(self, document_id: str, user_id: str) -> Dict:
        """Generate a summary of a specific document."""
        try:
            # This would require additional database queries to get document content
            # Implementation depends on your specific requirements
            pass
            
        except Exception as e:
            logger.error(f"Error generating document summary: {str(e)}")
            raise Exception(f"Failed to generate document summary: {str(e)}")

# Global instance
rag_service = RAGService()