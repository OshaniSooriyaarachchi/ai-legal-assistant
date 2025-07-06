from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
import os
import logging
import time

# Import your services
from services.document_processor import DocumentProcessor
from services.embedding_service import EmbeddingService
from services.vector_store import VectorStore
from services.rag_service import RAGService
from config.supabase_client import get_supabase_client

# Load environment variables
load_dotenv()

# Setup logging
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Legal Assistant API",
    description="Backend API for AI-powered legal document assistant with hybrid search",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class ChatRequest(BaseModel):
    query: str
    include_public: bool = True
    include_user_docs: bool = True

class ChatResponse(BaseModel):
    response: str
    sources: List[dict] = []
    processing_time_ms: int
    source_breakdown: dict = {}

class DocumentResponse(BaseModel):
    id: str
    filename: str
    status: str
    upload_date: str
    file_size: int
    source_type: str = "user"  # "user", "public", "session"

class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int

class ChatSessionRequest(BaseModel):
    title: Optional[str] = None

class ChatSessionResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str

# Initialize services
document_processor = DocumentProcessor()
embedding_service = EmbeddingService()
vector_store = VectorStore()
rag_service = RAGService()

# Simple auth middleware (replace with proper JWT validation)
async def get_current_user():
    """Simple user auth - replace with proper JWT validation"""
    # For now, return a dummy user - implement proper auth
    class DummyUser:
        def __init__(self):
            self.id = "f74ef22f-c9d1-4881-a329-b35ed6ceead6"
            self.email = "oshaninavodhya2001@gmail.com"
    
    return DummyUser()

# Admin role check (simplified)
async def verify_admin_role(user_id: str) -> bool:
    """Check if user has admin privileges"""
    try:
        supabase = get_supabase_client()
        result = supabase.table('user_roles').select('role').eq('user_id', user_id).eq('role', 'admin').eq('is_active', True).execute()
        return len(result.data) > 0
    except Exception as e:
        logger.error(f"Error verifying admin role: {str(e)}")
        return False

@app.get("/")
async def root():
    return {"message": "AI Legal Assistant API v2.0 is running with hybrid search!"}

@app.get("/health")
async def health_check():
    try:
        from config.supabase_client import supabase_client
        
        # Check if supabase_client is available and test connection
        if supabase_client and supabase_client.client:
            supabase_connected = await supabase_client.test_connection()
        else:
            supabase_connected = False
        
        return {
            "status": "healthy",
            "version": "2.0.0",
            "environment": os.getenv("ENVIRONMENT", "development"),
            "supabase_url": os.getenv("SUPABASE_URL", "Not configured"),
            "supabase_connected": supabase_connected,
            "gemini_api_configured": bool(os.getenv("GEMINI_API_KEY")),
            "features": {
                "hybrid_search": True,
                "chat_sessions": True,
                "admin_documents": True,
                "public_knowledge_base": True
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "version": "2.0.0"
        }

# =============================================================================
# DOCUMENT UPLOAD ENDPOINTS
# =============================================================================

@app.post("/api/documents/upload", response_model=dict)
async def upload_document(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user)
):
    """Upload and process a user document."""
    try:
        # Validate file type
        if not file.filename.lower().endswith(('.pdf', '.docx', '.txt')):
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Only PDF, DOCX, and TXT files are allowed."
            )
        
        # Process document through full pipeline
        result = await document_processor.process_document_full_pipeline(file, current_user.id)
        
        return {
            "status": "success",
            "message": "Document processed successfully",
            "document_id": result["document_id"],
            "filename": result["filename"],
            "file_type": result["file_type"],
            "character_count": result["character_count"],
            "total_chunks": result["total_chunks"],
            "processing_status": result["processing_status"],
            "chunks_with_embeddings": result["chunks_with_embeddings"],
            "source_type": "user"
        }
        
    except Exception as e:
        logger.error(f"Document upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

# =============================================================================
# ADMIN ENDPOINTS
# =============================================================================

@app.post("/api/admin/documents/upload", response_model=dict)
async def admin_upload_document(
    file: UploadFile = File(...),
    category: str = Form(...),
    current_user = Depends(get_current_user)
):
    """Admin upload to common knowledge base."""
    try:
        # Verify admin role
        is_admin = await verify_admin_role(current_user.id)
        if not is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        # Validate file type
        if not file.filename.lower().endswith(('.pdf', '.docx', '.txt')):
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Only PDF, DOCX, and TXT files are allowed."
            )
        
        # Process document and store as public
        document_data = await document_processor.process_upload(file)
        
        # Chunk and generate embeddings
        from utils.text_chunker import TextChunker
        chunker = TextChunker()
        chunks = chunker.chunk_text(
            document_data['text_content'],
            document_metadata={'filename': document_data['filename'], 'file_type': document_data['file_type']}
        )
        
        chunks_with_embeddings = await embedding_service.generate_chunk_embeddings(chunks)
        
        # Store as admin document
        document_id = await vector_store.store_admin_document(
            current_user.id, document_data, chunks_with_embeddings, category
        )
        
        return {
            "status": "success",
            "message": "Admin document uploaded to knowledge base",
            "document_id": document_id,
            "filename": document_data["filename"],
            "category": category,
            "total_chunks": len(chunks),
            "source_type": "public"
        }
        
    except Exception as e:
        logger.error(f"Admin document upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Admin upload failed: {str(e)}")

@app.get("/api/admin/documents")
async def list_admin_documents(current_user = Depends(get_current_user)):
    """List all public documents for admin management."""
    try:
        is_admin = await verify_admin_role(current_user.id)
        if not is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        documents = await vector_store.get_public_documents()
        
        return {
            "status": "success",
            "documents": documents,
            "total": len(documents)
        }
        
    except Exception as e:
        logger.error(f"Admin document listing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list admin documents: {str(e)}")

# =============================================================================
# CHAT SESSION ENDPOINTS
# =============================================================================

@app.post("/api/chat/sessions")
async def create_chat_session(
    request: ChatSessionRequest,
    current_user = Depends(get_current_user)
):
    """Create new chat session."""
    try:
        supabase = get_supabase_client()
        
        title = request.title or f"Chat {time.strftime('%Y-%m-%d %H:%M')}"
        
        result = supabase.table('chat_sessions').insert({
            'user_id': current_user.id,
            'title': title
        }).execute()
        
        if not result.data:
            raise Exception("Failed to create chat session")
        
        session = result.data[0]
        
        return {
            "status": "success",
            "session": {
                "id": session["id"],
                "title": session["title"],
                "created_at": session["created_at"],
                "updated_at": session["updated_at"]
            }
        }
        
    except Exception as e:
        logger.error(f"Chat session creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create chat session: {str(e)}")

@app.get("/api/chat/sessions")
async def get_user_chat_sessions(current_user = Depends(get_current_user)):
    """Get all chat sessions for user."""
    try:
        supabase = get_supabase_client()
        
        result = supabase.table('chat_sessions').select(
            'id, title, created_at, updated_at'
        ).eq('user_id', current_user.id).eq('is_active', True).order('updated_at', desc=True).execute()
        
        return {
            "status": "success",
            "sessions": result.data or [],
            "total": len(result.data) if result.data else 0
        }
        
    except Exception as e:
        logger.error(f"Chat session listing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list chat sessions: {str(e)}")

@app.get("/api/chat/sessions/{session_id}/history")
async def get_chat_history(
    session_id: str,
    limit: int = 50,
    current_user = Depends(get_current_user)
):
    """Get chat history for session."""
    try:
        supabase = get_supabase_client()
        
        result = supabase.table('query_history').select(
            'id, query_text, response_text, message_type, created_at, document_ids'
        ).eq('session_id', session_id).eq('user_id', current_user.id).order('created_at', desc=False).limit(limit).execute()
        
        return {
            "status": "success",
            "history": result.data or [],
            "total": len(result.data) if result.data else 0
        }
        
    except Exception as e:
        logger.error(f"Chat history retrieval failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get chat history: {str(e)}")

# =============================================================================
# CHAT/QUERY ENDPOINTS
# =============================================================================

@app.post("/api/chat/sessions/{session_id}/message", response_model=dict)
async def send_chat_message(
    session_id: str,
    request: ChatRequest,
    current_user = Depends(get_current_user)
):
    """Send message in chat session with hybrid search."""
    try:
        start_time = time.time()
        
        # Generate response using hybrid RAG
        result = await rag_service.generate_hybrid_response(
            query=request.query,
            user_id=current_user.id,
            session_id=session_id,
            include_public=request.include_public,
            include_user_docs=request.include_user_docs
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        result['processing_time_ms'] = processing_time
        
        # Store message in chat history
        supabase = get_supabase_client()
        
        # Store user query
        supabase.table('query_history').insert({
            'user_id': current_user.id,
            'session_id': session_id,
            'query_text': request.query,
            'message_type': 'user_query',
            'processing_time_ms': processing_time
        }).execute()
        
        # Store assistant response
        supabase.table('query_history').insert({
            'user_id': current_user.id,
            'session_id': session_id,
            'query_text': request.query,
            'response_text': result['response'],
            'message_type': 'assistant_response',
            'processing_time_ms': processing_time
        }).execute()
        
        return {
            "status": "success",
            **result
        }
        
    except Exception as e:
        logger.error(f"Chat message failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.post("/api/chat/sessions/{session_id}/upload")
async def upload_document_to_chat(
    session_id: str,
    file: UploadFile = File(...),
    current_user = Depends(get_current_user)
):
    """Upload document to specific chat session."""
    try:
        # Validate file type
        if not file.filename.lower().endswith(('.pdf', '.docx', '.txt')):
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Only PDF, DOCX, and TXT files are allowed."
            )
        
        # Process document and link to chat session
        document_data = await document_processor.process_upload(file)
        
        # Chunk and generate embeddings
        from utils.text_chunker import TextChunker
        chunker = TextChunker()
        chunks = chunker.chunk_text(
            document_data['text_content'],
            document_metadata={'filename': document_data['filename'], 'file_type': document_data['file_type']}
        )
        
        chunks_with_embeddings = await embedding_service.generate_chunk_embeddings(chunks)
        
        # Store document with session link
        document_id = await vector_store.store_processed_document(
            current_user.id, document_data, chunks_with_embeddings, session_id
        )
        
        # Add upload event to chat history
        supabase = get_supabase_client()
        supabase.table('query_history').insert({
            'user_id': current_user.id,
            'session_id': session_id,
            'query_text': f"Uploaded document: {file.filename}",
            'message_type': 'document_upload',
            'document_ids': [document_id]
        }).execute()
        
        return {
            "status": "success",
            "message": "Document uploaded to chat session",
            "document_id": document_id,
            "filename": document_data["filename"],
            "session_id": session_id,
            "total_chunks": len(chunks)
        }
        
    except Exception as e:
        logger.error(f"Document upload to chat failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

# =============================================================================
# LEGACY/GENERAL ENDPOINTS
# =============================================================================

@app.post("/api/chat", response_model=dict)
async def chat_query(
    request: ChatRequest,
    current_user = Depends(get_current_user)
):
    """General chat endpoint (legacy support)."""
    try:
        start_time = time.time()
        
        # Generate response using hybrid RAG (without session)
        result = await rag_service.generate_hybrid_response(
            query=request.query,
            user_id=current_user.id,
            include_public=request.include_public,
            include_user_docs=request.include_user_docs
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        result['processing_time_ms'] = processing_time
        
        return {
            "status": "success",
            **result
        }
        
    except Exception as e:
        logger.error(f"Chat query failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.get("/api/documents", response_model=dict)
async def list_documents(current_user = Depends(get_current_user)):
    """List all uploaded documents for the current user."""
    try:
        documents = await vector_store.get_user_documents(current_user.id)
        
        return {
            "status": "success",
            "documents": documents,
            "total": len(documents)
        }
        
    except Exception as e:
        logger.error(f"Document listing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

@app.get("/api/documents/public")
async def list_public_documents(category: str = None):
    """List public documents from knowledge base."""
    try:
        documents = await vector_store.get_public_documents(category)
        
        return {
            "status": "success",
            "documents": documents,
            "total": len(documents),
            "category": category
        }
        
    except Exception as e:
        logger.error(f"Public document listing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list public documents: {str(e)}")

@app.get("/api/chat/sessions/{session_id}/documents")
async def get_session_documents(
    session_id: str,
    current_user = Depends(get_current_user)
):
    """Get documents uploaded in specific chat session."""
    try:
        documents = await vector_store.get_chat_session_documents(session_id)
        
        return {
            "status": "success",
            "documents": documents,
            "total": len(documents),
            "session_id": session_id
        }
        
    except Exception as e:
        logger.error(f"Session document listing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list session documents: {str(e)}")

@app.delete("/api/documents/{document_id}")
async def delete_document(
    document_id: str,
    current_user = Depends(get_current_user)
):
    """Delete a document and its associated data."""
    try:
        success = await vector_store.delete_document(document_id, current_user.id)
        
        if success:
            return {
                "status": "success",
                "message": f"Document {document_id} deleted successfully"
            }
        else:
            raise HTTPException(status_code=404, detail="Document not found")
        
    except Exception as e:
        logger.error(f"Document deletion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)