import re
from typing import List, Dict, Optional
import tiktoken
from config.settings import settings

class TextChunker:
    """Advanced text chunking with overlap and metadata preservation."""
    
    def __init__(self):
        self.chunk_size = settings.chunk_size  # 1000 tokens
        self.chunk_overlap = settings.chunk_overlap  # 200 tokens
        self.encoding = tiktoken.get_encoding("cl100k_base")  # GPT-4 tokenizer
    
    def chunk_text(self, text: str, document_metadata: Dict = None) -> List[Dict]:
        """
        Split text into overlapping chunks with metadata.
        
        Args:
            text: Input text to chunk
            document_metadata: Document-level metadata
            
        Returns:
            List of chunk dictionaries with text and metadata
        """
        # Clean and normalize text
        cleaned_text = self._clean_text(text)
        
        # Split into sentences for better chunking boundaries
        sentences = self._split_into_sentences(cleaned_text)
        
        # Create chunks
        chunks = []
        current_chunk = ""
        current_tokens = 0
        chunk_index = 0
        
        for sentence in sentences:
            sentence_tokens = len(self.encoding.encode(sentence))
            
            # If adding this sentence would exceed chunk size, finalize current chunk
            if current_tokens + sentence_tokens > self.chunk_size and current_chunk:
                # Create chunk with metadata
                chunk_data = self._create_chunk_metadata(
                    current_chunk.strip(),
                    chunk_index,
                    document_metadata
                )
                chunks.append(chunk_data)
                
                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk)
                current_chunk = overlap_text + " " + sentence
                current_tokens = len(self.encoding.encode(current_chunk))
                chunk_index += 1
            else:
                current_chunk += " " + sentence
                current_tokens += sentence_tokens
        
        # Add final chunk
        if current_chunk.strip():
            chunk_data = self._create_chunk_metadata(
                current_chunk.strip(),
                chunk_index,
                document_metadata
            )
            chunks.append(chunk_data)
        
        return chunks
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep legal punctuation
        text = re.sub(r'[^\w\s\.\,\;\:\!\?\-\(\)\[\]\"\']+', ' ', text)
        return text.strip()
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences while preserving legal document structure."""
        # Handle legal document patterns
        text = re.sub(r'(\w)\.(\s+)([A-Z])', r'\1.\2\3', text)
        
        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _get_overlap_text(self, chunk: str) -> str:
        """Get overlap text from the end of current chunk."""
        tokens = self.encoding.encode(chunk)
        if len(tokens) <= self.chunk_overlap:
            return chunk
        
        overlap_tokens = tokens[-self.chunk_overlap:]
        return self.encoding.decode(overlap_tokens)
    
    def _create_chunk_metadata(self, chunk_text: str, chunk_index: int, 
                              document_metadata: Dict = None) -> Dict:
        """Create chunk with comprehensive metadata."""
        return {
            "chunk_text": chunk_text,
            "chunk_index": chunk_index,
            "token_count": len(self.encoding.encode(chunk_text)),
            "character_count": len(chunk_text),
            "word_count": len(chunk_text.split()),
            "document_metadata": document_metadata or {},
            "chapter_title": self._extract_chapter_info(chunk_text),
            "section_title": self._extract_section_info(chunk_text),
            "keywords": self._extract_keywords(chunk_text)
        }
    
    def _extract_chapter_info(self, text: str) -> Optional[str]:
        """Extract chapter information from text."""
        chapter_patterns = [
            r'CHAPTER\s+(\d+|[IVX]+)\s*[:\-]?\s*([^\n]+)',
            r'Chapter\s+(\d+|[IVX]+)\s*[:\-]?\s*([^\n]+)',
            r'SECTION\s+(\d+|[IVX]+)\s*[:\-]?\s*([^\n]+)'
        ]
        
        for pattern in chapter_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).strip()
        return None
    
    def _extract_section_info(self, text: str) -> Optional[str]:
        """Extract section information from text."""
        section_patterns = [
            r'Section\s+(\d+|[IVX]+)\s*[:\-]?\s*([^\n]+)',
            r'Subsection\s+(\d+|[IVX]+)\s*[:\-]?\s*([^\n]+)',
            r'Article\s+(\d+|[IVX]+)\s*[:\-]?\s*([^\n]+)'
        ]
        
        for pattern in section_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).strip()
        return None
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract legal keywords from text."""
        legal_keywords = [
            'contract', 'agreement', 'liability', 'damages', 'penalty',
            'violation', 'offense', 'regulation', 'statute', 'law',
            'court', 'judge', 'jury', 'evidence', 'testimony',
            'plaintiff', 'defendant', 'prosecution', 'defense'
        ]
        
        found_keywords = []
        text_lower = text.lower()
        
        for keyword in legal_keywords:
            if keyword in text_lower:
                found_keywords.append(keyword)
        
        return found_keywords