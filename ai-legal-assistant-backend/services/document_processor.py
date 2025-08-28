import logging
import tempfile
import os
from fastapi import UploadFile
from typing import Dict
import PyPDF2

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self):
        pass

    async def process_upload(self, file: UploadFile) -> Dict:
        try:
            # Create temporary file to store upload
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.filename.split('.')[-1]}") as temp_file:
                temp_file_path = temp_file.name
                
            try:
                # Write file content to temporary file
                content = await file.read()
                with open(temp_file_path, 'wb') as f:
                    f.write(content)
                
                # Calculate file size in bytes
                file_size_bytes = len(content)
                
                # Extract text based on file type
                file_extension = file.filename.split('.')[-1].lower()
                
                if file_extension == 'pdf':
                    text_content = self._extract_text_from_pdf(temp_file_path)
                elif file_extension in ['docx', 'doc']:
                    text_content = self._extract_text_from_docx(temp_file_path)
                elif file_extension == 'txt':
                    with open(temp_file_path, 'r', encoding='utf-8') as f:
                        text_content = f.read()
                else:
                    raise Exception(f"Unsupported file type: {file_extension}")
                
                result = {
                    "filename": file.filename,
                    "file_type": file_extension,
                    "text_content": text_content,
                    "character_count": len(text_content),
                    "size_bytes": file_size_bytes
                }
                
                return result
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_file_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temporary file: {str(e)}")
                    
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
            with open(file_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                text_content = []
                
                for page in pdf_reader.pages:
                    text_content.append(page.extract_text())
                    
            return '\n'.join(text_content)
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise Exception(f"Failed to extract text from PDF: {str(e)}")

    async def process_document_full_pipeline(self, file: UploadFile, user_id: str, 
                                        display_name: str = None, description: str = None) -> Dict:
        """Process document through full pipeline with proper file handling"""
        try:
            # ADD SUBSCRIPTION CHECKS BEFORE PROCESSING
            from services.enhanced_subscription_service import EnhancedSubscriptionService
            subscription_service = EnhancedSubscriptionService()
            
            # Read file content to check size first
            content = await file.read()
            await file.seek(0)  # Reset file pointer for processing
            document_size_mb = len(content) / (1024 * 1024)
            
            # Check subscription limits before processing
            subscription = await subscription_service.get_user_subscription_details(user_id)
            if not subscription:
                raise Exception("No active subscription found")
            
            # Check document size limit
            if not await subscription_service.check_document_size_limit(user_id, document_size_mb):
                raise Exception(f"Document size ({document_size_mb:.2f}MB) exceeds your plan limit ({subscription['max_document_size_mb']}MB)")
            
            # Check document count limit
            if not await subscription_service.check_document_count_limit(user_id):
                storage_info = await subscription_service.get_user_storage_info(user_id)
                raise Exception(f"Document count limit reached ({storage_info['document_count']}/{subscription['max_documents_per_user']})")
            # END OF SUBSCRIPTION CHECKS
            
            # Process the upload first
            document_data = await self.process_upload(file)
            
            # Add custom fields to document data (backward compatibility)
            if display_name:
                document_data['display_name'] = display_name
            else:
                document_data['display_name'] = document_data['filename']  # Fallback for backward compatibility
                
            if description:
                document_data['description'] = description
            else:
                document_data['description'] = ''  # Empty string for backward compatibility
            
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
                    'file_type': document_data['file_type'],
                    'display_name': document_data['display_name'],
                    'description': document_data['description']
                }
            )
            
            # Generate embeddings for chunks
            chunks_with_embeddings = await embedding_service.generate_chunk_embeddings(chunks)
            
            # Store in vector store
            document_id = await vector_store.store_processed_document(
                user_id, document_data, chunks_with_embeddings
            )
            
            # UPDATE STORAGE USAGE AFTER SUCCESSFUL PROCESSING
            await subscription_service.update_user_storage(user_id, document_size_mb, increment=True)
            
            return {
                "document_id": document_id,
                "display_name": document_data["display_name"],
                "description": document_data["description"],
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