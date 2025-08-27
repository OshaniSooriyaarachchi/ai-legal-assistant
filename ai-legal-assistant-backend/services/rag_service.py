import logging
from typing import List, Dict, Optional
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
import asyncio
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
        from config.supabase_client import get_supabase_client
        
        # Primary Gemini setup
        genai.configure(api_key=settings.gemini_api_key)
        self.model_primary = genai.GenerativeModel('gemini-1.5-flash')
        self.model = self.model_primary  # Keep for backward compatibility
        
        # Backup Gemini setup (if available)
        self.model_backup = None
        if hasattr(settings, 'gemini_api_key_backup') and getattr(settings, 'gemini_api_key_backup', None):
            # We'll configure this when needed to avoid conflicts
            self.backup_key = settings.gemini_api_key_backup
        
        self.prompt_templates = PromptTemplates()
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore()
        
    async def generate_with_fallback(self, prompt, generation_config=None):
        """Generate content with automatic fallback to backup API key."""
        try:
            # Try primary API key first
            response = await self.model_primary.generate_content_async(
                prompt,
                generation_config=generation_config
            )
            return response.text
            
        except ResourceExhausted as e:
            logger.warning("Primary Gemini API rate limit exceeded, trying backup...")
            
            if hasattr(self, 'backup_key'):
                try:
                    # Configure backup API key
                    genai.configure(api_key=self.backup_key)
                    backup_model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    response = await backup_model.generate_content_async(
                        prompt,
                        generation_config=generation_config
                    )
                    
                    # Switch back to primary for next attempt
                    genai.configure(api_key=settings.gemini_api_key)
                    
                    return response.text
                    
                except Exception as backup_error:
                    logger.error(f"Backup API also failed: {backup_error}")
                    # Switch back to primary
                    genai.configure(api_key=settings.gemini_api_key)
                    raise e
            else:
                raise e
                
        except Exception as e:
            logger.error(f"Generation error: {str(e)}")
            raise e
        
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
                                     conversation_history: str = "",
                                     user_type: str = "normal") -> Dict:
        """
        Generate response using hybrid search across multiple sources.
        
        Args:
            query: User query
            user_id: User ID for document access
            session_id: Optional chat session ID
            include_public: Whether to search public knowledge base
            include_user_docs: Whether to search user documents
            conversation_history: Previous conversation context
            user_type: Type of user ("normal" or "lawyer") for response styling
            
        Returns:
            Generated response with categorized sources
        """
        try:
            # Import here to avoid circular imports
            from services.hybrid_search_service import HybridSearchService
            
            # Initialize hybrid search service
            hybrid_search = HybridSearchService()
            
            # Perform hybrid search
            search_results = await hybrid_search.hybrid_search(
                query=query,
                user_id=user_id,
                include_public=include_public,
                include_user_docs=include_user_docs,
                session_id=session_id,
                limit=settings.top_k
            )
            
            # Extract relevant chunks from search results
            relevant_chunks = search_results.get('results', [])

            # Build context from multiple sources
            context = self._build_hybrid_context(relevant_chunks)
            
            # Get session context if available
            session_context = search_results.get('session_context', '')
            
            # Generate response using Gemini with hybrid context and user type
            # Modified to return both prompt and response for admin viewing
            generation_result = await self._generate_with_hybrid_context_and_user_type_detailed(
                query=query,
                context=context,
                session_context=session_context,
                conversation_history=conversation_history,
                user_type=user_type
            )
            
            # Prepare response with source attribution and admin data
            return {
                'response': generation_result['response'],
                'gemini_prompt': generation_result.get('prompt'),           # NEW: For admin viewing
                'gemini_raw_response': generation_result.get('raw_response'), # NEW: For admin viewing
                'sources': relevant_chunks,
                'source_breakdown': search_results.get('source_breakdown', {}),
                'session_context_used': bool(session_context),
                'search_params': search_results.get('search_params', {})
            }
            
        except Exception as e:
            logger.error(f"Error generating hybrid response: {str(e)}")
            raise Exception(f"Failed to generate hybrid response: {str(e)}")

    async def _generate_with_context(self, query: str, context: str, 
                                   conversation_history: Optional[List[Dict]] = None) -> str:
        """Generate response using Gemini with context (legacy method)."""
        try:
            # Build conversation context
            conversation_context = ""
            if conversation_history:
                conversation_context = self._build_conversation_context(conversation_history)
            
            # Create prompt
            prompt = await self.prompt_templates.create_rag_prompt(
                query=query,
                context=context,
                conversation_history=conversation_context
            )
            
            # Generate response
            response_text = await self.generate_with_fallback(
                prompt,
                genai.types.GenerationConfig(
                    temperature=settings.temperature,
                    max_output_tokens=2048,
                )
            )
            
            return response_text
            
        except Exception as e:
            logger.error(f"Error generating with context: {str(e)}")
            return "I apologize, but I'm unable to generate a response at the moment. Please try again."

    async def _generate_with_hybrid_context(self, query: str, context: str, 
                                          session_context: str = "",
                                          conversation_history: str = "") -> str:
        """Generate response using hybrid context with source attribution"""
        try:
            # Create hybrid prompt
            prompt = await self.prompt_templates.create_hybrid_rag_prompt(
                query=query,
                context=context,
                session_context=session_context,
                conversation_history=conversation_history
            )
            
            # Generate response
            response_text = await self.generate_with_fallback(
                prompt,
                genai.types.GenerationConfig(
                    temperature=0.7,  # Slightly higher for more natural flow
                    max_output_tokens=2048,
                )
            )
            
            return response_text
            
        except Exception as e:
            logger.error(f"Error generating response with hybrid context: {str(e)}")
            raise Exception(f"Failed to generate response: {str(e)}")

    async def _generate_with_hybrid_context_and_user_type(self, query: str, context: str, 
                                                        session_context: str = "",
                                                        conversation_history: str = "",
                                                        user_type: str = "normal") -> str:
        """Generate response using hybrid context with user type consideration"""
        try:
            # Create user-type-aware prompt
            prompt = await self.prompt_templates.create_hybrid_rag_prompt_with_user_type(
                query=query,
                context=context,
                user_type=user_type,
                session_context=session_context,
                conversation_history=conversation_history
            )
            
            # Adjust generation config based on user type
            if user_type == "lawyer":
                generation_config = genai.types.GenerationConfig(
                    temperature=0.3,  # Lower temperature for more precise legal language
                    max_output_tokens=3000,  # Allow more tokens for detailed analysis
                )
            else:
                generation_config = genai.types.GenerationConfig(
                    temperature=0.7,  # Higher temperature for more natural explanations
                    max_output_tokens=2048,
                )
            
            response_text = await self.generate_with_fallback(prompt, generation_config)
            return response_text
            
        except Exception as e:
            logger.error(f"Error generating response with user type context: {str(e)}")
            raise Exception(f"Failed to generate response: {str(e)}")

    async def _generate_with_hybrid_context_and_user_type_detailed(self, query: str, context: str, 
                                                                session_context: str = "",
                                                                conversation_history: str = "",
                                                                user_type: str = "normal") -> Dict:
        """Generate response and return detailed data including prompt and raw response for admin viewing"""
        try:
            # Create user-type-aware prompt
            prompt = await self.prompt_templates.create_hybrid_rag_prompt_with_user_type(
                query=query,
                context=context,
                user_type=user_type,
                session_context=session_context,
                conversation_history=conversation_history
            )
            
            # Adjust generation config based on user type
            if user_type == "lawyer":
                generation_config = genai.types.GenerationConfig(
                    temperature=0.3,  # Lower temperature for more precise legal language
                    max_output_tokens=3000,  # Allow more tokens for detailed analysis
                )
            else:
                generation_config = genai.types.GenerationConfig(
                    temperature=0.7,  # Higher temperature for more natural explanations
                    max_output_tokens=2048,
                )
            
            # Generate response and capture raw response
            raw_response = await self.generate_with_fallback(prompt, generation_config)
            
            return {
                'prompt': prompt,
                'raw_response': raw_response,
                'response': raw_response  # For now, they're the same
            }
            
        except Exception as e:
            logger.error(f"Error generating response with user type context: {str(e)}")
            raise Exception(f"Failed to generate response: {str(e)}")

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

    def _build_hybrid_context(self, chunks: List[Dict]) -> str:
        """Build context from multiple sources with source attribution"""
        if not chunks:
            return "Based on general legal knowledge and procedures:"
        
        context_parts = []
        
        # Group chunks by source type
        public_chunks = [c for c in chunks if c.get('source_type') == 'public']
        user_chunks = [c for c in chunks if c.get('source_type') == 'user']
        session_chunks = [c for c in chunks if c.get('source_type') == 'session']
        
        # Add public knowledge base context
        if public_chunks:
            context_parts.append("=== LEGAL KNOWLEDGE BASE ===")
            for chunk in public_chunks:
                doc_title = chunk.get('document_title', 'Unknown Document')
                category = chunk.get('document_category', 'General')
                content = chunk.get('chunk_content', '')
                
                context_parts.append(f"Source: {doc_title} ({category})")
                context_parts.append(f"Content: {content}")
                context_parts.append("---")
        
        # Add user document context
        if user_chunks:
            context_parts.append("=== YOUR DOCUMENTS ===")
            for chunk in user_chunks:
                doc_title = chunk.get('document_title', 'Unknown Document')
                content = chunk.get('chunk_content', '')
                
                context_parts.append(f"Source: {doc_title}")
                context_parts.append(f"Content: {content}")
                context_parts.append("---")
        
        # Add session-specific context
        if session_chunks:
            context_parts.append("=== CURRENT SESSION DOCUMENTS ===")
            for chunk in session_chunks:
                doc_title = chunk.get('document_title', 'Unknown Document')
                content = chunk.get('chunk_content', '')
                
                context_parts.append(f"Source: {doc_title}")
                context_parts.append(f"Content: {content}")
                context_parts.append("---")
        
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
            
            # Generate summary using dynamic prompt
            from services.prompt_management_service import PromptManagementService
            prompt_service = PromptManagementService()
            
            prompt = await prompt_service.format_prompt('rag_document_summary', {'document_text': full_text})
            
            response_text = await self.generate_with_fallback(
                prompt,
                genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=512,
                )
            )
            
            return {'summary': response_text}
            
        except Exception as e:
            logger.error(f"Error generating document summary: {str(e)}")
            raise Exception(f"Failed to generate document summary: {str(e)}")

# Global instance
rag_service = RAGService()