import logging
from typing import List, Dict, Optional
import google.generativeai as genai
from services.embedding_service import EmbeddingService
from services.vector_store import VectorStore
from utils.text_chunker import TextChunker
from utils.prompt_templates import PromptTemplates
from config.settings import settings

logger = logging.getLogger(__name__)

class RAGService:
    """Enhanced Retrieval-Augmented Generation service with hybrid search support."""
    
    def __init__(self):
        """Initialize RAG service."""
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        self.prompt_templates = PromptTemplates()
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore()
        
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
            chunker = TextChunker()
            chunks = chunker.chunk_text(
                text_content,
                document_metadata={
                    'filename': document_data['filename'],
                    'file_type': document_data['file_type']
                }
            )
            
            logger.info(f"Created {len(chunks)} chunks from document")
            
            # Generate embeddings for chunks
            chunks_with_embeddings = await self.embedding_service.generate_chunk_embeddings(chunks)
            
            # Store in vector database
            document_id = await self.vector_store.store_processed_document(
                user_id=user_id,
                document_data=document_data,
                chunks_with_embeddings=chunks_with_embeddings
            )
            
            logger.info(f"Document processed and stored with ID: {document_id}")
            return document_id
            
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            raise Exception(f"Failed to process document: {str(e)}")
    
    async def generate_response(self, query: str, user_id: str, 
                              conversation_history: Optional[List[Dict]] = None) -> Dict:
        """
        Generate a response to a legal query using RAG (legacy method).
        
        Args:
            query: User query
            user_id: User ID for document access
            conversation_history: Previous conversation context
            
        Returns:
            Generated response with sources
        """
        try:
            # Generate query embedding
            query_embedding = await self.embedding_service.generate_query_embedding(query)
            
            # Retrieve relevant chunks using legacy method
            relevant_chunks = await self.vector_store.similarity_search(
                query_embedding=query_embedding,
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

    async def generate_hybrid_response(self, query: str, user_id: str, 
                                     session_id: str = None,
                                     include_public: bool = True,
                                     include_user_docs: bool = True,
                                     conversation_history: Optional[List[Dict]] = None) -> Dict:
        """
        Generate response using hybrid search across multiple sources.
        
        Args:
            query: User query
            user_id: User ID for document access
            session_id: Optional chat session ID
            include_public: Whether to search public knowledge base
            include_user_docs: Whether to search user documents
            conversation_history: Previous conversation context
            
        Returns:
            Generated response with categorized sources
        """
        try:
            # Generate query embedding
            query_embedding = await self.embedding_service.generate_query_embedding(query)
            
            # Perform hybrid search
            search_results = await self.vector_store.hybrid_similarity_search(
                query_embedding=query_embedding,
                user_id=user_id,
                include_public=include_public,
                include_user_docs=include_user_docs,
                session_id=session_id,
                limit=settings.top_k
            )
            
            # Build hybrid context from multiple sources
            context = self._build_hybrid_context(search_results)
            
            # Build conversation context
            conversation_context = ""
            if conversation_history:
                conversation_context = self._build_conversation_context(conversation_history)
            
            # Generate response with hybrid context
            response = await self._generate_with_hybrid_context(
                query=query,
                context=context,
                conversation_context=conversation_context
            )
            
            # Prepare response with categorized sources
            return {
                'response': response,
                'sources': self._format_hybrid_sources(search_results),
                'context_used': self._has_context(search_results),
                'source_breakdown': {
                    'public_sources': len(search_results.get('public_results', [])),
                    'user_sources': len(search_results.get('user_results', [])),
                    'session_sources': len(search_results.get('session_results', []))
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating hybrid response: {str(e)}")
            return {
                'response': 'I apologize, but I encountered an error processing your request. Please try again.',
                'sources': [],
                'context_used': False,
                'source_breakdown': {
                    'public_sources': 0,
                    'user_sources': 0,
                    'session_sources': 0
                }
            }

    async def _generate_with_context(self, query: str, context: str, 
                                   conversation_history: Optional[List[Dict]] = None) -> str:
        """Generate response using Gemini with context (legacy method)."""
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

    async def _generate_with_hybrid_context(self, query: str, context: str, 
                                          conversation_context: str = "") -> str:
        """Generate response using Gemini with hybrid context from multiple sources."""
        try:
            # Create hybrid prompt template
            prompt = f"""You are an expert Sri Lankan legal advisor. Based on the provided legal passages from multiple sources, answer the user's question accurately and comprehensively.

{context}

CONVERSATION CONTEXT:
{conversation_context}

USER QUESTION:
{query}

Instructions:
1. Base your answer primarily on the provided legal passages
2. Prioritize information from the common legal knowledge base for general legal principles
3. Use user document context for specific case details and personal documents
4. Use session documents for context specific to this conversation
5. Clearly distinguish between general legal principles and document-specific information
6. If information from different sources conflicts, explain the differences
7. Maintain conversation context from previous messages
8. If the passages don't contain sufficient information, clearly state this
9. Provide specific legal references when available
10. Use clear, accessible language while maintaining legal accuracy

RESPONSE:"""

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
            logger.error(f"Error generating with hybrid context: {str(e)}")
            return "I apologize, but I'm unable to generate a response at the moment. Please try again."

    def _build_context(self, relevant_chunks: List[Dict]) -> str:
        """Build context string from relevant chunks (legacy method)."""
        if not relevant_chunks:
            return "No relevant context found in your documents."
        
        context_parts = []
        for i, chunk in enumerate(relevant_chunks, 1):
            similarity_score = chunk.get('similarity_score', 0)
            filename = chunk.get('document_title', chunk.get('filename', 'Unknown'))
            context_parts.append(
                f"[Source {i}: {filename} (Relevance: {similarity_score:.2f})]\n"
                f"{chunk.get('chunk_content', chunk.get('chunk_text', ''))}\n"
            )
        
        return "\n".join(context_parts)

    def _build_hybrid_context(self, search_results: Dict) -> str:
        """Build context from multiple sources with clear source attribution."""
        context_parts = []
        
        # Add public knowledge base results
        if search_results.get('public_results'):
            context_parts.append("=== COMMON LEGAL KNOWLEDGE BASE ===")
            for i, result in enumerate(search_results['public_results'], 1):
                category = result.get('document_category', 'General')
                title = result.get('document_title', 'Unknown')
                context_parts.append(f"[Public Source {i}: {title} - {category}]")
                context_parts.append(result.get('chunk_content', ''))
                context_parts.append("")
        
        # Add user document results
        if search_results.get('user_results'):
            context_parts.append("=== YOUR PERSONAL DOCUMENTS ===")
            for i, result in enumerate(search_results['user_results'], 1):
                title = result.get('document_title', 'Unknown')
                context_parts.append(f"[Your Document {i}: {title}]")
                context_parts.append(result.get('chunk_content', ''))
                context_parts.append("")
        
        # Add session-specific results
        if search_results.get('session_results'):
            context_parts.append("=== DOCUMENTS FROM THIS CONVERSATION ===")
            for i, result in enumerate(search_results['session_results'], 1):
                title = result.get('document_title', 'Unknown')
                context_parts.append(f"[Session Document {i}: {title}]")
                context_parts.append(result.get('chunk_content', ''))
                context_parts.append("")
        
        if not context_parts:
            return "No relevant context found in any available documents."
        
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
        """Format source information for response (legacy method)."""
        sources = []
        seen_files = set()
        
        for chunk in relevant_chunks:
            filename = chunk.get('document_title', chunk.get('filename', 'Unknown'))
            if filename not in seen_files:
                sources.append({
                    'filename': filename,
                    'file_type': chunk.get('file_type', 'unknown'),
                    'similarity_score': chunk.get('similarity_score', 0),
                    'chunk_preview': chunk.get('chunk_content', chunk.get('chunk_text', ''))[:200] + "..."
                })
                seen_files.add(filename)
        
        return sources

    def _format_hybrid_sources(self, search_results: Dict) -> List[Dict]:
        """Format source information from hybrid search results."""
        sources = []
        
        # Format public sources
        for result in search_results.get('public_results', []):
            sources.append({
                'filename': result.get('document_title', 'Unknown'),
                'source_type': 'public',
                'category': result.get('document_category', 'General'),
                'similarity_score': result.get('similarity_score', 0),
                'chunk_preview': result.get('chunk_content', '')[:200] + "..."
            })
        
        # Format user sources
        for result in search_results.get('user_results', []):
            sources.append({
                'filename': result.get('document_title', 'Unknown'),
                'source_type': 'user',
                'similarity_score': result.get('similarity_score', 0),
                'chunk_preview': result.get('chunk_content', '')[:200] + "..."
            })
        
        # Format session sources
        for result in search_results.get('session_results', []):
            sources.append({
                'filename': result.get('document_title', 'Unknown'),
                'source_type': 'session',
                'similarity_score': result.get('similarity_score', 0),
                'chunk_preview': result.get('chunk_content', '')[:200] + "..."
            })
        
        return sources

    def _has_context(self, search_results: Dict) -> bool:
        """Check if any context was found in search results."""
        return (len(search_results.get('public_results', [])) > 0 or 
                len(search_results.get('user_results', [])) > 0 or 
                len(search_results.get('session_results', [])) > 0)
    
    async def get_document_summary(self, document_id: str, user_id: str) -> Dict:
        """Generate a summary of a specific document."""
        try:
            # Get document chunks
            chunks = await self.vector_store.get_document_chunks(document_id)
            
            if not chunks:
                return {'summary': 'Document not found or no content available.'}
            
            # Combine chunks for summary
            full_text = ' '.join([chunk['chunk_content'] for chunk in chunks[:5]])  # First 5 chunks
            
            # Generate summary
            prompt = f"""Provide a concise summary of this legal document:

{full_text}

Summary:"""
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=512,
                )
            )
            
            return {'summary': response.text}
            
        except Exception as e:
            logger.error(f"Error generating document summary: {str(e)}")
            raise Exception(f"Failed to generate document summary: {str(e)}")

# Global instance
rag_service = RAGService()