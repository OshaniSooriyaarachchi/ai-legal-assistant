import tempfile
import os
from pathlib import Path
from typing import Dict
import logging
from fastapi import UploadFile

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self):
        pass

    async def process_upload(self, file: UploadFile) -> Dict:
        """Process uploaded file with proper file handling"""
        try:
            # Create a temporary file with proper cleanup
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.filename.split('.')[-1]}") as temp_file:
                # Read file content in chunks
                content = await file.read()
                temp_file.write(content)
                temp_file.flush()
                
                # Process the temporary file
                file_path = temp_file.name
                
            try:
                # Extract text from the temporary file
                if file.filename.lower().endswith('.docx'):
                    text_content = self._extract_text_from_docx(file_path)
                elif file.filename.lower().endswith('.pdf'):
                    text_content = self._extract_text_from_pdf(file_path)
                else:
                    # For TXT files
                    with open(file_path, 'r', encoding='utf-8') as f:
                        text_content = f.read()
                
                # Process the text content
                result = {
                    'filename': file.filename,
                    'file_type': Path(file.filename).suffix,
                    'text_content': text_content,
                    'size_bytes': len(content),
                    'character_count': len(text_content),
                    'word_count': len(text_content.split())
                }
                
                return result
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(file_path)
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file: {e}")
                    
        except Exception as e:
            logger.error(f"Error processing upload: {str(e)}")
            raise Exception(f"Failed to process upload: {str(e)}")

    def _extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX file with proper error handling"""
        try:
            from docx import Document
            
            # Open document with proper handling
            doc = Document(file_path)
            text_content = []
            
            for paragraph in doc.paragraphs:
                text_content.append(paragraph.text)
                
            return '\n'.join(text_content)
            
        except Exception as e:
            logger.error(f"Error extracting text from DOCX: {str(e)}")
            raise Exception(f"Failed to extract text from DOCX: {str(e)}")

    def _extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file with proper error handling"""
        try:
            import PyPDF2
            
            with open(file_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                text_content = []
                
                for page in pdf_reader.pages:
                    text_content.append(page.extract_text())
                    
            return '\n'.join(text_content)
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise Exception(f"Failed to extract text from PDF: {str(e)}")

    async def process_document_full_pipeline(self, file: UploadFile, user_id: str) -> Dict:
        """Process document through full pipeline with proper file handling"""
        try:
            # Process the upload first
            document_data = await self.process_upload(file)
            
            # Import services here to avoid circular imports
            from services.embedding_service import EmbeddingService
            from services.vector_store import VectorStore
            from utils.text_chunker import TextChunker
            
            # Initialize services
            embedding_service = EmbeddingService()
            vector_store = VectorStore()
            chunker = TextChunker()
            
            # Chunk the text
            chunks = chunker.chunk_text(
                document_data['text_content'],
                document_metadata={
                    'filename': document_data['filename'], 
                    'file_type': document_data['file_type']
                }
            )
            
            # Generate embeddings for chunks
            chunks_with_embeddings = await embedding_service.generate_chunk_embeddings(chunks)
            
            # Store in vector store
            document_id = await vector_store.store_processed_document(
                user_id, document_data, chunks_with_embeddings
            )
            
            return {
                "document_id": document_id,
                "filename": document_data["filename"],
                "file_type": document_data["file_type"],
                "character_count": document_data["character_count"],
                "total_chunks": len(chunks),
                "processing_status": "completed",
                "chunks_with_embeddings": len(chunks_with_embeddings)
            }
            
        except Exception as e:
            logger.error(f"Error in full pipeline processing: {str(e)}")
            raise Exception(f"Failed to process document: {str(e)}")