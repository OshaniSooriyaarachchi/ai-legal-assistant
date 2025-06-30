import logging
from typing import List, Optional
import google.generativeai as genai
from config.settings import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Service for generating text embeddings using Google Gemini API."""
    
    def __init__(self):
        """Initialize the embedding service with Gemini API."""
        genai.configure(api_key=settings.gemini_api_key)
        self.model_name = settings.embedding_model
        
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        try:
            if not text or not text.strip():
                raise ValueError("Text cannot be empty")
            
            # Clean and prepare text
            cleaned_text = self._clean_text(text)
            
            # Generate embedding using Gemini
            result = genai.embed_content(
                model=self.model_name,
                content=cleaned_text,
                task_type="retrieval_document"
            )
            
            return result['embedding']
            
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise Exception(f"Failed to generate embedding: {str(e)}")
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        try:
            embeddings = []
            
            for text in texts:
                if text and text.strip():
                    embedding = await self.generate_embedding(text)
                    embeddings.append(embedding)
                else:
                    logger.warning("Skipping empty text in batch")
                    
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {str(e)}")
            raise Exception(f"Failed to generate batch embeddings: {str(e)}")
    
    async def generate_query_embedding(self, query: str) -> List[float]:
        """
        Generate embedding for a query text.
        
        Args:
            query: Query text to embed
            
        Returns:
            Query embedding vector
        """
        try:
            if not query or not query.strip():
                raise ValueError("Query cannot be empty")
            
            # Clean and prepare query
            cleaned_query = self._clean_text(query)
            
            # Generate embedding with query task type
            result = genai.embed_content(
                model=self.model_name,
                content=cleaned_query,
                task_type="retrieval_query"
            )
            
            return result['embedding']
            
        except Exception as e:
            logger.error(f"Error generating query embedding: {str(e)}")
            raise Exception(f"Failed to generate query embedding: {str(e)}")
    
    def _clean_text(self, text: str) -> str:
        """Clean and preprocess text for embedding."""
        # Remove excessive whitespace
        text = ' '.join(text.split())
        
        # Truncate if too long (Gemini has token limits)
        max_chars = 30000  # Conservative limit
        if len(text) > max_chars:
            text = text[:max_chars]
            logger.warning(f"Text truncated to {max_chars} characters")
        
        return text
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by the model."""
        # Gemini embedding-001 produces 768-dimensional vectors
        return 768

# Global instance
embedding_service = EmbeddingService()