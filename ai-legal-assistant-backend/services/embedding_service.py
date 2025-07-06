# services/embedding_service.py - Enhanced version
import logging
from typing import List, Optional, Dict
import google.generativeai as genai
import asyncio
from config.settings import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Enhanced embedding service for document chunks."""
    
    def __init__(self):
        """Initialize the embedding service with Gemini API."""
        genai.configure(api_key=settings.gemini_api_key)
        self.model_name = settings.embedding_model
        self.batch_size = 10  # Process embeddings in batches
        
    async def generate_chunk_embeddings(self, chunks: List[Dict]) -> List[Dict]:
        """
        Generate embeddings for document chunks.
        
        Args:
            chunks: List of chunk dictionaries from TextChunker
            
        Returns:
            List of chunks with embeddings added
        """
        try:
            # Process chunks in batches
            processed_chunks = []
            
            print(f"\n=== PROCESSING {len(chunks)} CHUNKS ===")
            
            for i in range(0, len(chunks), self.batch_size):
                batch = chunks[i:i + self.batch_size]
                batch_texts = [chunk["chunk_text"] for chunk in batch]
                
                print(f"\n--- BATCH {i//self.batch_size + 1} ---")
                print(f"Batch size: {len(batch_texts)}")
                
                # Print each chunk being sent to Gemini
                for j, text in enumerate(batch_texts):
                    print(f"\nCHUNK {i + j + 1}:")
                    print(f"Length: {len(text)} characters")
                    print(f"Content: {text[:150]}..." if len(text) > 150 else f"Content: {text}")
                    print(f"Word count: {len(text.split())}")
                
                # Generate embeddings for batch
                print(f"\nSending batch to Gemini API...")
                batch_embeddings = await self.generate_embeddings_batch(batch_texts)
                
                print(f"Received {len(batch_embeddings)} embeddings from Gemini")
                
                # Add embeddings to chunks
                for idx, (chunk, embedding) in enumerate(zip(batch, batch_embeddings)):
                    chunk["embedding"] = embedding
                    chunk["embedding_model"] = self.model_name
                    chunk["embedding_dimensions"] = len(embedding)
                    
                    # Print embedding info
                    print(f"\nEMBEDDING {i + idx + 1}:")
                    print(f"Dimensions: {len(embedding)}")
                    print(f"First 5 values: {embedding[:5]}")
                    print(f"Last 5 values: {embedding[-5:]}")
                    print(f"Min: {min(embedding):.6f}, Max: {max(embedding):.6f}")
                
                processed_chunks.extend(batch)
                
                # Small delay to respect API rate limits
                await asyncio.sleep(0.1)
            
            print(f"\n=== EMBEDDING GENERATION COMPLETE ===")
            print(f"Total processed chunks: {len(processed_chunks)}")
            logger.info(f"Generated embeddings for {len(processed_chunks)} chunks")
            return processed_chunks
            
        except Exception as e:
            logger.error(f"Error generating chunk embeddings: {str(e)}")
            raise Exception(f"Failed to generate chunk embeddings: {str(e)}")
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        try:
            if not text or not text.strip():
                raise ValueError("Text cannot be empty")
            
            cleaned_text = self._clean_text(text)
            
            # Print what we're sending to Gemini
            print(f"\n--- SINGLE EMBEDDING REQUEST ---")
            print(f"Original text length: {len(text)}")
            print(f"Cleaned text length: {len(cleaned_text)}")
            print(f"Model: {self.model_name}")
            print(f"Text preview: {cleaned_text[:200]}..." if len(cleaned_text) > 200 else f"Text: {cleaned_text}")
            
            result = genai.embed_content(
                model=self.model_name,
                content=cleaned_text,
                task_type="retrieval_document"
            )
            
            embedding = result['embedding']
            
            # Print what we got back
            print(f"\n--- EMBEDDING RESPONSE ---")
            print(f"Embedding dimensions: {len(embedding)}")
            print(f"First 3 values: {embedding[:3]}")
            print(f"Last 3 values: {embedding[-3:]}")
            print(f"Min: {min(embedding):.6f}, Max: {max(embedding):.6f}")
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            print(f"ERROR: Failed to generate embedding for text: {text[:100]}...")
            raise Exception(f"Failed to generate embedding: {str(e)}")
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        try:
            embeddings = []
            
            for text in texts:
                embedding = await self.generate_embedding(text)
                embeddings.append(embedding)
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {str(e)}")
            raise Exception(f"Failed to generate batch embeddings: {str(e)}")
    
    async def generate_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for search queries."""
        try:
            cleaned_query = self._clean_text(query)
            
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
        """Clean text for embedding generation."""
        if not text:
            return ""
        
        original_length = len(text)
        
        # Remove excessive whitespace
        cleaned = ' '.join(text.split())
        
        # Truncate if too long (Gemini has input limits)
        max_chars = 20000  # Conservative limit
        if len(cleaned) > max_chars:
            cleaned = cleaned[:max_chars]
            print(f"WARNING: Text truncated from {original_length} to {len(cleaned)} characters")
        
        if original_length != len(cleaned):
            print(f"Text cleaning: {original_length} → {len(cleaned)} characters")
        
        return cleaned