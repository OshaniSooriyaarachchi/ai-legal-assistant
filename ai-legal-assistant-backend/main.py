from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
import os
import logging
import time
import jwt
import requests

from services.document_processor import DocumentProcessor
from services.embedding_service import EmbeddingService
from services.vector_store import VectorStore
from services.rag_service import RAGService
from config.supabase_client import get_supabase_client
from config.settings import settings

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Legal Assistant API",
    description="Backend API for AI-powered legal document assistant with hybrid search",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins_list(),  # Use settings
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

# Initialize security
security = HTTPBearer()

# Auth middleware
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Extract user from Supabase JWT token"""
    try:
        # Get the JWT token from the Authorization header
        token = credentials.credentials
        
        # Verify the JWT token with Supabase
        supabase = get_supabase_client()
        
        # Use Supabase to verify the token and get user info
        try:
            user_response = supabase.auth.get_user(token)
            
            if not user_response.user:
                raise HTTPException(status_code=401, detail="Invalid authentication token")
            
            # Create user object with actual user data
            class AuthenticatedUser:
                def __init__(self, user_data):
                    self.id = user_data.id
                    self.email = user_data.email
            
            return AuthenticatedUser(user_response.user)
            
        except Exception as supabase_error:
            logger.error(f"Supabase auth error: {str(supabase_error)}")
            # Fallback: try to decode JWT manually for debugging
            try:
                # Decode without verification for debugging (not recommended for production)
                decoded = jwt.decode(token, options={"verify_signature": False})
                user_id = decoded.get('sub')
                user_email = decoded.get('email', 'unknown@example.com')
                
                if user_id:
                    class AuthenticatedUser:
                        def __init__(self, user_id, email):
                            self.id = user_id
                            self.email = email
                    
                    return AuthenticatedUser(user_id, user_email)
                else:
                    raise HTTPException(status_code=401, detail="Invalid token payload")
            except Exception as jwt_error:
                logger.error(f"JWT decode error: {str(jwt_error)}")
                raise HTTPException(status_code=401, detail="Invalid authentication token")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

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
            'title': title,
            'is_active': True  # Explicitly set as active
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
        
        # Query for sessions that are either explicitly active (is_active = true) or NULL (default)
        result = supabase.table('chat_sessions').select(
            'id, title, created_at, updated_at, is_active'
        ).eq('user_id', current_user.id).or_('is_active.eq.true,is_active.is.null').order('updated_at', desc=True).execute()
        
        # Filter out any explicitly inactive sessions
        active_sessions = []
        for session in (result.data or []):
            if session.get('is_active') is not False:  # Include True and NULL
                active_sessions.append({
                    'id': session['id'],
                    'title': session['title'],
                    'created_at': session['created_at'],
                    'updated_at': session['updated_at']
                })
        
        return {
            "status": "success",
            "sessions": active_sessions,
            "total": len(active_sessions)
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

@app.delete("/api/chat/sessions/{session_id}/history")
async def clear_chat_history(
    session_id: str,
    current_user = Depends(get_current_user)
):
    """Clear all chat history for a session (delete from query_history table)."""
    try:
        supabase = get_supabase_client()
        logger.info(f"Attempting to clear chat history for session {session_id} for user {current_user.id}")
        
        # First, verify the session belongs to the user and exists
        session_result = supabase.table('chat_sessions').select('id, user_id').eq('id', session_id).eq('user_id', current_user.id).execute()
        
        if not session_result.data:
            logger.warning(f"Chat session {session_id} not found for user {current_user.id}")
            raise HTTPException(status_code=404, detail="Chat session not found or access denied")
        
        # Delete all query history for this session
        logger.info(f"Deleting query history for session {session_id}")
        history_delete = supabase.table('query_history').delete().eq('session_id', session_id).eq('user_id', current_user.id).execute()
        
        deleted_count = len(history_delete.data) if history_delete.data else 0
        logger.info(f"Query history deletion result: {deleted_count} records deleted")
        
        return {
            "status": "success", 
            "message": f"Chat history cleared for session {session_id}",
            "deleted_count": deleted_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat history clearing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to clear chat history: {str(e)}")

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
        
        # Store complete conversation in single record
        supabase = get_supabase_client()
        
        supabase.table('query_history').insert({
            'user_id': current_user.id,
            'session_id': session_id,
            'query_text': request.query,
            'response_text': result['response'],
            'message_type': 'conversation',
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
    
@app.delete("/api/chat/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    current_user = Depends(get_current_user)
):
    """Delete a chat session and all its associated data."""
    try:
        supabase = get_supabase_client()
        logger.info(f"Attempting to delete chat session {session_id} for user {current_user.id}")
        
        # First, verify the session belongs to the user and exists
        session_result = supabase.table('chat_sessions').select('id, user_id, is_active').eq('id', session_id).eq('user_id', current_user.id).execute()
        
        if not session_result.data:
            logger.warning(f"Chat session {session_id} not found for user {current_user.id}")
            raise HTTPException(status_code=404, detail="Chat session not found or access denied")
        
        session_info = session_result.data[0]
        logger.info(f"Found session: {session_info}")
        
        # Delete related query history first (due to foreign key constraints)
        logger.info(f"Deleting query history for session {session_id}")
        history_delete = supabase.table('query_history').delete().eq('session_id', session_id).eq('user_id', current_user.id).execute()
        logger.info(f"Query history deletion result: {len(history_delete.data) if history_delete.data else 0} records deleted")
        
        # Delete the chat session (hard delete)
        logger.info(f"Hard-deleting chat session {session_id}")
        session_delete = supabase.table('chat_sessions').delete().eq('id', session_id).eq('user_id', current_user.id).execute()
        
        logger.info(f"Session deletion result: {session_delete.data}")
        
        if not session_delete.data:
            logger.error(f"Failed to update session {session_id} - no data returned")
            raise HTTPException(status_code=500, detail="Failed to delete chat session")
        
        logger.info(f"Successfully soft-deleted chat session {session_id} for user {current_user.id}")
        
        # Optional: Also delete session-specific documents if they exist
        # Note: This assumes documents table has session_id column - skip if it doesn't exist
        try:
            # Check if documents table has session_id column by trying a test query
            test_query = supabase.table('documents').select('id').limit(1).execute()
            if test_query.data:
                # Get column info to check if session_id exists
                sample_doc = test_query.data[0]
                # Only try to update documents if we can confirm the column exists
                # For now, we'll skip this since the column doesn't exist in your schema
                pass
        except Exception as doc_error:
            # Log but don't fail the entire operation
            logger.warning(f"Could not delete session documents: {str(doc_error)}")
        
        return {
            "status": "success",
            "message": f"Chat session {session_id} deleted successfully",
            "session_id": session_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat session deletion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete chat session: {str(e)}")

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

@app.get("/api/documents/{document_id}")
async def get_document(
    document_id: str,
    current_user = Depends(get_current_user)
):
    """Get a specific document by ID"""
    try:
        supabase = get_supabase_client()
        
        # Get document with access control
        result = supabase.table('documents').select(
            'id, title, file_name, file_size, file_type, upload_date, '
            'processing_status, is_public, document_category, metadata'
        ).eq('id', document_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Document not found")
        
        document = result.data[0]
        
        # Check if user has access to this document
        if not document['is_public'] and document.get('user_id') != current_user.id:
            # Check if user is admin for private documents
            is_admin = await verify_admin_role(current_user.id)
            if not is_admin:
                raise HTTPException(status_code=403, detail="Access denied")
        
        return {
            "status": "success",
            "document": {
                "id": document["id"],
                "title": document["title"],
                "file_name": document["file_name"],
                "file_size": document["file_size"],
                "file_type": document["file_type"],
                "upload_date": document["upload_date"],
                "processing_status": document["processing_status"],
                "is_public": document["is_public"],
                "document_category": document.get("document_category"),
                "metadata": document.get("metadata", {}),
                "source_type": "public" if document["is_public"] else "user"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get document: {str(e)}")    
    
@app.get("/api/documents")
async def list_user_documents(
    current_user = Depends(get_current_user)
):
    """List all documents accessible to the user"""
    try:
        supabase = get_supabase_client()
        
        # Get user's own documents + public documents
        result = supabase.table('documents').select(
            'id, title, file_name, file_size, file_type, upload_date, '
            'processing_status, is_public, document_category, metadata'
        ).or_(
            f'user_id.eq.{current_user.id},and(is_public.eq.true,is_active.eq.true)'
        ).order('upload_date', desc=True).execute()
        
        documents = []
        for doc in result.data or []:
            documents.append({
                "id": doc["id"],
                "title": doc["title"],
                "file_name": doc["file_name"],
                "file_size": doc["file_size"],
                "file_type": doc["file_type"],
                "upload_date": doc["upload_date"],
                "processing_status": doc["processing_status"],
                "is_public": doc["is_public"],
                "document_category": doc.get("document_category"),
                "source_type": "public" if doc["is_public"] else "user"
            })
        
        return {
            "status": "success",
            "documents": documents,
            "total": len(documents)
        }
        
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

@app.delete("/api/documents/{document_id}")
async def delete_document(
    document_id: str,
    current_user = Depends(get_current_user)
):
    """Delete a document"""
    try:
        success = await vector_store.delete_document(document_id, current_user.id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Document not found or access denied")
        
        return {
            "status": "success",
            "message": "Document deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")
    


@app.patch("/api/admin/documents/{document_id}/status")
async def toggle_document_status(
    document_id: str,
    status_update: dict,  # {"is_active": true/false}
    current_user = Depends(get_current_user)
):
    """Toggle document active/inactive status"""
    try:
        # Verify admin role
        is_admin = await verify_admin_role(current_user.id)
        if not is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        from services.admin_service import AdminService
        admin_service = AdminService()
        
        success = await admin_service.activate_deactivate_document(
            current_user.id,
            document_id,
            status_update.get("is_active", True)
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {
            "status": "success",
            "message": f"Document status updated",
            "document_id": document_id,
            "is_active": status_update.get("is_active")
        }
        
    except Exception as e:
        logger.error(f"Error updating document status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/admin/documents/{document_id}")
async def delete_admin_document(
    document_id: str,
    current_user = Depends(get_current_user)
):
    """Delete an admin document from knowledge base"""
    print("Verifying admin role for user:", current_user.id)
    try:
        # Verify admin role
        print("Verifying admin role for user:", current_user.id)
        is_admin = await verify_admin_role(current_user.id)
        if not is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        from services.admin_service import AdminService
        admin_service = AdminService()
        
        success = await admin_service.delete_public_document(current_user.id, document_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {
            "status": "success",
            "message": "Document deleted successfully",
            "document_id": document_id
        }
        
    except Exception as e:
        logger.error(f"Error deleting admin document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/statistics")
async def get_admin_statistics(current_user = Depends(get_current_user)):
    """Get admin dashboard statistics"""
    try:
        # Verify admin role
        is_admin = await verify_admin_role(current_user.id)
        if not is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        from services.admin_service import AdminService
        admin_service = AdminService()
        
        stats = await admin_service.get_admin_statistics(current_user.id)
        
        return {
            "status": "success",
            "statistics": stats
        }
        
    except Exception as e:
        logger.error(f"Error getting admin statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    


#temporary login endpoint for testing

@app.post("/api/auth/login")
async def login_for_testing(credentials: dict):
    """Temporary login endpoint for testing - REMOVE IN PRODUCTION"""
    try:
        supabase = get_supabase_client()
        
        email = credentials.get("email")
        password = credentials.get("password")
        
        if not email or not password:
            raise HTTPException(status_code=400, detail="Email and password required")
        
        # Login with Supabase
        auth_response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if auth_response.user and auth_response.session:
            return {
                "access_token": auth_response.session.access_token,
                "user_id": auth_response.user.id,
                "email": auth_response.user.email
            }
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")
            
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Login failed: {str(e)}")