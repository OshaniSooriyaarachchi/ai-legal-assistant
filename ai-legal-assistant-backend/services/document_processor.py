import os
import logging
from typing import List, Dict, Optional
from pathlib import Path
import fitz  # PyMuPDF
from docx import Document
from fastapi import UploadFile, HTTPException

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Service for processing and extracting text from various document formats."""
    
    def __init__(self):
        self.supported_extensions = {'.pdf', '.docx', '.txt'}
    
    async def process_upload(self, file: UploadFile) -> Dict[str, any]:
        """
        Process an uploaded file and extract text content.
        
        Args:
            file: FastAPI UploadFile object
            
        Returns:
            Dict containing extracted text and metadata
        """
        if not self._is_supported_file(file.filename):
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type. Supported types: {', '.join(self.supported_extensions)}"
            )
        
        try:
            content = await file.read()
            file_extension = Path(file.filename).suffix.lower()
            
            if file_extension == '.pdf':
                text = self._extract_pdf_text(content)
            elif file_extension == '.docx':
                text = self._extract_docx_text(content)
            elif file_extension == '.txt':
                text = content.decode('utf-8')
            else:
                raise HTTPException(status_code=400, detail="Unsupported file type")
            
            return {
                'filename': file.filename,
                'file_type': file_extension,
                'text_content': text,
                'character_count': len(text),
                'word_count': len(text.split()),
                'size_bytes': len(content)
            }
            
        except Exception as e:
            logger.error(f"Error processing file {file.filename}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    
    def _extract_pdf_text(self, content: bytes) -> str:
        """Extract text from PDF content."""
        try:
            doc = fitz.open("pdf", content)
            text = ""
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                text += page.get_text()
                text += "\n\n"  # Add page break
            
            doc.close()
            return text.strip()
            
        except Exception as e:
            logger.error(f"Error extracting PDF text: {str(e)}")
            raise Exception(f"Failed to extract text from PDF: {str(e)}")
    
    def _extract_docx_text(self, content: bytes) -> str:
        """Extract text from DOCX content."""
        try:
            # Save content to temporary file for python-docx
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp_file:
                tmp_file.write(content)
                tmp_file.flush()
                
                doc = Document(tmp_file.name)
                text = ""
                
                for paragraph in doc.paragraphs:
                    text += paragraph.text + "\n"
                
                # Extract text from tables
                for table in doc.tables:
                    for row in table.rows:
                        for cell in row.cells:
                            text += cell.text + " "
                        text += "\n"
                
                # Clean up temporary file
                os.unlink(tmp_file.name)
                
                return text.strip()
                
        except Exception as e:
            logger.error(f"Error extracting DOCX text: {str(e)}")
            raise Exception(f"Failed to extract text from DOCX: {str(e)}")
    
    def _is_supported_file(self, filename: str) -> bool:
        """Check if the file type is supported."""
        if not filename:
            return False
        
        file_extension = Path(filename).suffix.lower()
        return file_extension in self.supported_extensions
    
    def validate_file_size(self, file_size: int, max_size: int = 10 * 1024 * 1024) -> bool:
        """Validate file size is within limits."""
        return file_size <= max_size

# Global instance
document_processor = DocumentProcessor()