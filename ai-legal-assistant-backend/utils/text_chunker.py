import re
from typing import List

class TextChunker:
    """Utility for chunking text into smaller segments for embedding."""
    
    def chunk_text(self, text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
        """
        Split text into overlapping chunks.
        
        Args:
            text: Input text to chunk
            chunk_size: Maximum characters per chunk
            chunk_overlap: Number of overlapping characters between chunks
            
        Returns:
            List of text chunks
        """
        if not text or not text.strip():
            return []
        
        # Clean text
        text = self._clean_text(text)
        
        # Try to split by sentences first
        sentences = self._split_into_sentences(text)
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            # If adding this sentence would exceed chunk size
            if len(current_chunk) + len(sentence) > chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                
                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk, chunk_overlap)
                current_chunk = overlap_text + sentence
            else:
                current_chunk += " " + sentence if current_chunk else sentence
        
        # Add the last chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        # Handle very long sentences that exceed chunk_size
        final_chunks = []
        for chunk in chunks:
            if len(chunk) <= chunk_size:
                final_chunks.append(chunk)
            else:
                # Split long chunks by words
                sub_chunks = self._split_long_chunk(chunk, chunk_size, chunk_overlap)
                final_chunks.extend(sub_chunks)
        
        return final_chunks
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)\[\]\{\}\"\'\/]', '', text)
        
        return text.strip()
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting on periods, exclamation marks, and question marks
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _get_overlap_text(self, text: str, overlap_size: int) -> str:
        """Get the last part of text for overlap."""
        if len(text) <= overlap_size:
            return text
        
        # Try to find a good break point (end of sentence)
        overlap_text = text[-overlap_size:]
        
        # Find the first sentence end in the overlap
        match = re.search(r'[.!?]\s+', overlap_text)
        if match:
            return overlap_text[match.end():]
        
        return overlap_text
    
    def _split_long_chunk(self, chunk: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """Split a chunk that's too long into smaller pieces."""
        words = chunk.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            word_length = len(word) + 1  # +1 for space
            
            if current_length + word_length > chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                
                # Create overlap
                overlap_words = self._get_overlap_words(current_chunk, chunk_overlap)
                current_chunk = overlap_words + [word]
                current_length = sum(len(w) + 1 for w in current_chunk)
            else:
                current_chunk.append(word)
                current_length += word_length
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def _get_overlap_words(self, words: List[str], overlap_size: int) -> List[str]:
        """Get overlap words from the end of current chunk."""
        text = ' '.join(words)
        if len(text) <= overlap_size:
            return words
        
        # Get words that fit in overlap size
        overlap_words = []
        current_length = 0
        
        for word in reversed(words):
            word_length = len(word) + 1
            if current_length + word_length <= overlap_size:
                overlap_words.insert(0, word)
                current_length += word_length
            else:
                break
        
        return overlap_words

# Global instance
text_chunker = TextChunker()