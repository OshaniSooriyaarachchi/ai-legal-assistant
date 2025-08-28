import sys
import os
from pathlib import Path


current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))


from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
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

from services.rate_limiting_service import RateLimitingService
from api.rate_limit_middleware import check_query_rate_limit, increment_query_count

from services.admin_package_service import AdminPackageService
from services.enhanced_subscription_service import EnhancedSubscriptionService
from services.prompt_management_service import PromptManagementService


from pydantic import BaseModel
from typing import List

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


from api import signup

app = FastAPI(
    title="AI Legal Assistant API",
    description="Backend API for AI-powered legal document assistant with hybrid search",
    version="2.0.0"
)

# Register signup router
app.include_router(signup.router)

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
    user_type: Optional[str] = "normal"  # "normal" or "lawyer"

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

# Review models
class ChatReviewRequest(BaseModel):
    rating: Optional[int] = None
    comment: Optional[str] = None
    skipped: bool = False

class ChatReviewResponse(BaseModel):
    id: str
    session_id: str
    user_id: str
    rating: Optional[int]
    comment: Optional[str]
    skipped: bool
    created_at: str

# Admin Package Management Models
class PackageCreateRequest(BaseModel):
    name: str
    display_name: str
    daily_query_limit: int  # -1 for unlimited
    max_document_size_mb: int
    max_documents_per_user: int
    price_monthly: float
    features: List[str]
    is_active: bool = True

class PackageUpdateRequest(BaseModel):
    name: str
    display_name: str
    daily_query_limit: int
    max_document_size_mb: int
    max_documents_per_user: int
    price_monthly: float
    features: List[str]
    is_active: bool

class AssignPackageRequest(BaseModel):
    user_id: str
    package_id: str

# Prompt Management Models
class PromptTemplateRequest(BaseModel):
    name: str
    title: str
    description: Optional[str] = ""
    template_content: str
    placeholders: List[str] = []
    category: str = "system"
    user_type: str = "all"  # "all", "normal", "lawyer"
    is_active: bool = True

class PromptTemplateUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    template_content: Optional[str] = None
    placeholders: Optional[List[str]] = None
    category: Optional[str] = None
    user_type: Optional[str] = None
    is_active: Optional[bool] = None

class PromptFormatRequest(BaseModel):
    template_name: str
    variables: dict
    user_type: str = "all"

# Initialize services
document_processor = DocumentProcessor()
embedding_service = EmbeddingService()
vector_store = VectorStore()
rag_service = RAGService()
rate_limiting_service = RateLimitingService()
prompt_management_service = PromptManagementService()

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


async def check_rate_limit_with_user(current_user = Depends(get_current_user)):
    """Rate limit check that properly gets current user"""
    return await check_query_rate_limit(current_user)


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
    display_name: str = Form(...),
    description: str = Form(...),
    current_user = Depends(get_current_user)
):
    """Upload and process a user document."""
    try:
        # Validate required fields
        if not display_name.strip():
            raise HTTPException(status_code=400, detail="Document name is required")
        if not description.strip():
            raise HTTPException(status_code=400, detail="Document description is required")
            
        # Validate file type
        if not file.filename.lower().endswith(('.pdf', '.docx', '.txt')):
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Only PDF, DOCX, and TXT files are allowed."
            )
        
        # Process document through full pipeline
        result = await document_processor.process_document_full_pipeline(
            file, current_user.id, display_name.strip(), description.strip()
        )
        
        return {
            "status": "success",
            "message": "Document processed successfully",
            "document_id": result["document_id"],
            "display_name": result.get("display_name", display_name),
            "description": result.get("description", description),
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
    display_name: str = Form(...),
    description: str = Form(...),
    current_user = Depends(get_current_user)
):
    """Admin upload to common knowledge base."""
    try:
        # Verify admin role
        is_admin = await verify_admin_role(current_user.id)
        if not is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        # Validate required fields
        if not display_name.strip():
            raise HTTPException(status_code=400, detail="Document name is required")
        if not description.strip():
            raise HTTPException(status_code=400, detail="Document description is required")
        
        # Validate file type
        if not file.filename.lower().endswith(('.pdf', '.docx', '.txt')):
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Only PDF, DOCX, and TXT files are allowed."
            )
        
        # Process document and store as public
        document_data = await document_processor.process_upload(file)
        
        # Add custom fields to document data
        document_data['display_name'] = display_name.strip()
        document_data['description'] = description.strip()
        
        # Chunk and generate embeddings
        from utils.text_chunker import TextChunker
        chunker = TextChunker()
        chunks = chunker.chunk_text(
            document_data['text_content'],
            document_metadata={
                'filename': document_data['filename'], 
                'file_type': document_data['file_type'],
                'display_name': display_name.strip(),
                'description': description.strip()
            }
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
            "display_name": display_name.strip(),
            "description": description.strip(),
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
    current_user = Depends(get_current_user),  # Get user FIRST
    rate_limit_info = Depends(check_rate_limit_with_user)  # Use the wrapper function
):
    """Send message in chat session with hybrid search."""
    try:
        start_time = time.time()
        
        # Check if this is the first message in the session
        from services.chat_service import ChatService
        chat_service = ChatService()
        history = await chat_service.get_chat_history(session_id, limit=1)
        is_first_message = len(history) == 0
        
        # Generate response using hybrid RAG
        result = await rag_service.generate_hybrid_response(
            query=request.query,
            user_id=current_user.id,
            session_id=session_id,
            include_public=request.include_public,
            include_user_docs=False,
            user_type=request.user_type
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        result['processing_time_ms'] = processing_time
        
        # Store complete conversation in single record with admin data
        supabase = get_supabase_client()
        
        supabase.table('query_history').insert({
            'user_id': current_user.id,
            'session_id': session_id,
            'query_text': request.query,
            'response_text': result['response'],
            'gemini_prompt': result.get('gemini_prompt'),        # NEW: For admin viewing
            'gemini_raw_response': result.get('gemini_raw_response'), # NEW: For admin viewing
            'message_type': 'conversation',
            'processing_time_ms': processing_time
        }).execute()
        
        # Update title if this is the first message
        if is_first_message:
            await chat_service.update_session_title_from_message(
                session_id, current_user.id, request.query
            )
        
        # INCREMENT USAGE AFTER SUCCESSFUL QUERY
        await increment_query_count(current_user)
        
        return {
            "status": "success",
            **result
        }
        
    except Exception as e:
        logger.error(f"Chat message failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


# =============================================================================
# CHAT SESSION REVIEW ENDPOINTS
# =============================================================================

@app.get("/api/chat/sessions/{session_id}/review", response_model=dict)
async def get_chat_session_review(
    session_id: str,
    current_user = Depends(get_current_user)
):
    """Get existing review (or skip) status for a chat session for current user."""
    try:
        supabase = get_supabase_client()

        # Verify ownership of session
        session_res = supabase.table('chat_sessions').select('id, user_id').eq('id', session_id).eq('user_id', current_user.id).execute()
        if not session_res.data:
            raise HTTPException(status_code=404, detail="Chat session not found")

        review_res = supabase.table('chat_session_reviews').select(
            'id, session_id, user_id, rating, comment, skipped, created_at'
        ).eq('session_id', session_id).eq('user_id', current_user.id).limit(1).execute()

        if review_res.data:
            review = review_res.data[0]
            return {"status": "success", "has_review": True, "review": review}
        else:
            return {"status": "success", "has_review": False, "review": None}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get chat session review: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get review")


@app.post("/api/chat/sessions/{session_id}/review", response_model=dict)
async def submit_chat_session_review(
    session_id: str,
    review: ChatReviewRequest,
    current_user = Depends(get_current_user)
):
    """Submit a review or mark skip for the chat session. Only one per user per session."""
    try:
        supabase = get_supabase_client()

        # Ownership check
        session_res = supabase.table('chat_sessions').select('id, user_id').eq('id', session_id).eq('user_id', current_user.id).execute()
        if not session_res.data:
            raise HTTPException(status_code=404, detail="Chat session not found")

        # Validate rating unless skipped
        if not review.skipped:
            if review.rating is None:
                raise HTTPException(status_code=400, detail="Rating required unless skipped")
            if review.rating < 1 or review.rating > 5:
                raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

        # Check existing review
        existing = supabase.table('chat_session_reviews').select('id').eq('session_id', session_id).eq('user_id', current_user.id).limit(1).execute()
        if existing.data:
            raise HTTPException(status_code=409, detail="Review already submitted")

        insert_data = {
            'session_id': session_id,
            'user_id': current_user.id,
            'rating': review.rating,
            'comment': review.comment,
            'skipped': review.skipped
        }
        inserted = supabase.table('chat_session_reviews').insert(insert_data).execute()
        if not inserted.data:
            raise HTTPException(status_code=500, detail="Failed to save review")

        return {"status": "success", "review": inserted.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit chat session review: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to submit review")



@app.put("/api/chat/sessions/{session_id}/title")
async def update_session_title(
    session_id: str,
    request: dict,
    current_user = Depends(get_current_user)
):
    """Update chat session title"""
    try:
        title = request.get('title', '').strip()
        if not title:
            raise HTTPException(status_code=400, detail="Title cannot be empty")
        
        from services.chat_service import ChatService
        chat_service = ChatService()
        success = await chat_service.update_session_title(session_id, current_user.id, title)
        
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"status": "success", "title": title}
        
    except Exception as e:
        logger.error(f"Failed to update session title: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update title")

@app.post("/api/chat/sessions/{session_id}/upload")
async def upload_document_to_chat(
    session_id: str,
    file: UploadFile = File(...),
    display_name: str = Form(...),
    description: str = Form(...),
    current_user = Depends(get_current_user)
):
    """Upload document to specific chat session."""
    try:
        # Validate required fields
        if not display_name.strip():
            raise HTTPException(status_code=400, detail="Document name is required")
        if not description.strip():
            raise HTTPException(status_code=400, detail="Document description is required")
            
        # Validate file type
        if not file.filename.lower().endswith(('.pdf', '.docx', '.txt')):
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Only PDF, DOCX, and TXT files are allowed."
            )
        
        # Process document and link to chat session
        document_data = await document_processor.process_upload(file)
        
        # Add custom fields to document data
        document_data['display_name'] = display_name.strip()
        document_data['description'] = description.strip()
        
        # Chunk and generate embeddings
        from utils.text_chunker import TextChunker
        chunker = TextChunker()
        chunks = chunker.chunk_text(
            document_data['text_content'],
            document_metadata={
                'filename': document_data['filename'], 
                'file_type': document_data['file_type'],
                'display_name': display_name.strip(),
                'description': description.strip()
            }
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
            'query_text': f"Uploaded document: {display_name.strip()}",
            'message_type': 'document_upload',
            'document_ids': [document_id],
            'gemini_prompt': None,  # No AI interaction for document uploads
            'gemini_raw_response': None  # No AI interaction for document uploads
        }).execute()
        
        return {
            "status": "success",
            "message": "Document uploaded to chat session",
            "document_id": document_id,
            "display_name": display_name.strip(),
            "description": description.strip(),
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
    rate_limit_info = Depends(check_query_rate_limit),  # ADD RATE LIMITING CHECK
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
            include_user_docs=False,  # only search current session + public
            user_type=request.user_type
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        result['processing_time_ms'] = processing_time
        
        # INCREMENT USAGE AFTER SUCCESSFUL QUERY
        await increment_query_count(current_user)
        
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

@app.get("/api/admin/users/chats")
async def get_all_user_chats(current_user = Depends(get_current_user)):
    """Get all user chats across all users for admin view"""
    try:
        # Verify admin role
        is_admin = await verify_admin_role(current_user.id)
        if not is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        supabase = get_supabase_client()
        
        # Get all active chat sessions without profile joins
        result = supabase.table('chat_sessions').select(
            'id, title, created_at, updated_at, user_id'
        ).or_('is_active.eq.true,is_active.is.null').order('updated_at', desc=True).execute()
        
        chats = []
        for session in (result.data or []):
            # Ensure timestamps are properly formatted with timezone info
            created_at = session.get('created_at')
            updated_at = session.get('updated_at')
            
            # Handle timezone conversion for Sri Lankan time
            if created_at:
                # If no timezone info, assume UTC and add 'Z'
                if not created_at.endswith('Z') and '+' not in created_at and 'T' in created_at:
                    created_at = created_at + 'Z'
                elif 'T' not in created_at:
                    # If it's just a date, add time and timezone
                    created_at = created_at + 'T00:00:00Z'
            
            if updated_at:
                # If no timezone info, assume UTC and add 'Z'
                if not updated_at.endswith('Z') and '+' not in updated_at and 'T' in updated_at:
                    updated_at = updated_at + 'Z'
                elif 'T' not in updated_at:
                    # If it's just a date, add time and timezone
                    updated_at = updated_at + 'T00:00:00Z'
            
            chats.append({
                'session_id': session['id'],
                'title': session['title'],
                'user_id': session['user_id'],
                'user_email': f"user-{session['user_id'][:8]}",  # Simple user identifier
                'created_at': created_at,
                'updated_at': updated_at
            })
        
        return {
            "status": "success",
            "chats": chats,
            "total": len(chats)
        }
        
    except Exception as e:
        logger.error(f"Error getting all user chats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get user chats: {str(e)}")

@app.get("/api/admin/users/{user_id}/chats")
async def get_user_chats_by_admin(
    user_id: str,
    current_user = Depends(get_current_user)
):
    """Get all chats for a specific user (admin view)"""
    try:
        # Verify admin role
        is_admin = await verify_admin_role(current_user.id)
        if not is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        supabase = get_supabase_client()
        
        # Get user's chat sessions
        result = supabase.table('chat_sessions').select(
            'id, title, created_at, updated_at'
        ).eq('user_id', user_id).or_('is_active.eq.true,is_active.is.null').order('updated_at', desc=True).execute()
        
        # Get user email
        user_result = supabase.table('profiles').select('email').eq('id', user_id).execute()
        user_email = user_result.data[0]['email'] if user_result.data else "Unknown"
        
        chats = []
        for session in (result.data or []):
            chats.append({
                'session_id': session['id'],
                'title': session['title'],
                'created_at': session['created_at'],
                'updated_at': session['updated_at']
            })
        
        return {
            "status": "success",
            "user_id": user_id,
            "user_email": user_email,
            "chats": chats,
            "total": len(chats)
        }
        
    except Exception as e:
        logger.error(f"Error getting user chats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get user chats: {str(e)}")

@app.get("/api/admin/sessions/{session_id}/history")
async def get_chat_history_admin(
    session_id: str,
    current_user = Depends(get_current_user)
):
    """Get chat history for any session (admin view)"""
    try:
        # Verify admin role
        is_admin = await verify_admin_role(current_user.id)
        if not is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        supabase = get_supabase_client()
        
        # Get session info with user details
        session_result = supabase.table('chat_sessions').select(
            '''
            id, title, user_id, created_at,
            profiles!chat_sessions_user_id_fkey(email)
            '''
        ).eq('id', session_id).execute()
        
        if not session_result.data:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        session_info = session_result.data[0]
        user_email = "Unknown"
        if session_info.get('profiles'):
            user_email = session_info['profiles'].get('email', 'Unknown')
        
        # Get chat history with admin fields
        history_result = supabase.table('query_history').select(
            'id, query_text, response_text, gemini_prompt, gemini_raw_response, '
            'message_type, created_at, document_ids'
        ).eq('session_id', session_id).order('created_at', desc=False).execute()
        
        # Process history timestamps
        processed_history = []
        for item in (history_result.data or []):
            created_at = item.get('created_at')
            if created_at:
                # Ensure proper timezone format
                if not created_at.endswith('Z') and '+' not in created_at and 'T' in created_at:
                    created_at = created_at + 'Z'
                elif 'T' not in created_at:
                    created_at = created_at + 'T00:00:00Z'
                item['created_at'] = created_at
            processed_history.append(item)
        
        return {
            "status": "success",
            "session_info": {
                "session_id": session_info['id'],
                "title": session_info['title'],
                "user_id": session_info['user_id'],
                "user_email": user_email,
                "created_at": session_info['created_at']
            },
            "history": processed_history,
            "total": len(processed_history)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chat history for admin: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get chat history: {str(e)}")

@app.get("/api/admin/users/documents")
async def get_all_user_documents(current_user = Depends(get_current_user)):
    """Get all user documents across all users for admin view"""
    try:
        # Verify admin role
        is_admin = await verify_admin_role(current_user.id)
        if not is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        supabase = get_supabase_client()
        
        # Get all user documents (non-public) without profile joins
        result = supabase.table('documents').select(
            'id, title, file_name, file_size, file_type, upload_date, processing_status, user_id, is_active'
        ).eq('is_public', False).order('upload_date', desc=True).execute()
        
        documents = []
        for doc in (result.data or []):
            documents.append({
                'document_id': doc['id'],
                'title': doc['title'],
                'file_name': doc['file_name'],
                'file_size': doc['file_size'],
                'file_type': doc['file_type'],
                'upload_date': doc['upload_date'],
                'processing_status': doc['processing_status'],
                'user_id': doc['user_id'],
                'user_email': f"user-{doc['user_id'][:8]}",  # Simple user identifier
                'is_active': doc.get('is_active', True)
            })
        
        return {
            "status": "success",
            "documents": documents,
            "total": len(documents)
        }
        
    except Exception as e:
        logger.error(f"Error getting all user documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get user documents: {str(e)}")

@app.get("/api/admin/users/{user_id}/documents")
async def get_user_documents_by_admin(
    user_id: str,
    current_user = Depends(get_current_user)
):
    """Get all documents for a specific user (admin view)"""
    try:
        # Verify admin role
        is_admin = await verify_admin_role(current_user.id)
        if not is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        supabase = get_supabase_client()
        
        # Get user's documents
        result = supabase.table('documents').select(
            'id, title, file_name, file_size, file_type, upload_date, processing_status, is_active'
        ).eq('user_id', user_id).eq('is_public', False).order('upload_date', desc=True).execute()
        
        documents = []
        for doc in (result.data or []):
            documents.append({
                'document_id': doc['id'],
                'title': doc['title'],
                'file_name': doc['file_name'],
                'file_size': doc['file_size'],
                'file_type': doc['file_type'],
                'upload_date': doc['upload_date'],
                'processing_status': doc['processing_status'],
                'is_active': doc.get('is_active', True)
            })
        
        return {
            "status": "success",
            "user_id": user_id,
            "user_email": f"user-{user_id[:8]}",  # Simple user identifier
            "documents": documents,
            "total": len(documents)
        }
        
    except Exception as e:
        logger.error(f"Error getting user documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get user documents: {str(e)}")
    


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
    


# =============================================================================
# SUBSCRIPTION ENDPOINTS
# =============================================================================

@app.get("/api/subscription/plans")
async def get_subscription_plans():
    """Get all available subscription plans"""
    try:
        plans = await rate_limiting_service.get_subscription_plans()
        return {
            "status": "success",
            "plans": plans
        }
    except Exception as e:
        logger.error(f"Error getting subscription plans: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get subscription plans")

@app.get("/api/subscription/current")
async def get_current_subscription(current_user = Depends(get_current_user)):
    """Get user's current subscription and usage"""
    try:
        subscription = await rate_limiting_service.get_user_subscription(current_user.id)
        daily_usage = await rate_limiting_service.get_daily_usage(current_user.id)
        
        return {
            "status": "success",
            "subscription": subscription,
            "daily_usage": daily_usage,
            "remaining_queries": subscription['daily_limit'] - daily_usage if subscription['daily_limit'] != -1 else -1
        }
    except Exception as e:
        logger.error(f"Error getting current subscription: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get subscription info")

@app.post("/api/subscription/upgrade")
async def upgrade_subscription(
    request: dict,  # {"plan_name": "premium"}
    current_user = Depends(get_current_user)
):
    """Upgrade user subscription (simplified - integrate with payment processor)"""
    try:
        plan_name = request.get("plan_name")
        if not plan_name:
            raise HTTPException(status_code=400, detail="Plan name is required")
        
        # In production, you would:
        # 1. Process payment with Stripe/PayPal
        # 2. Verify payment success
        # 3. Then upgrade the subscription
        
        success = await rate_limiting_service.upgrade_user_subscription(
            current_user.id, plan_name
        )
        
        if success:
            return {
                "status": "success",
                "message": f"Successfully upgraded to {plan_name} plan"
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to upgrade subscription")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error upgrading subscription: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upgrade subscription")

@app.get("/api/usage/history")
async def get_usage_history(
    days: int = 30,
    current_user = Depends(get_current_user)
):
    """Get user's query usage history"""
    try:
        # Calculate date range
        from datetime import date, timedelta
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        supabase = get_supabase_client()
        result = supabase.table('daily_query_usage').select(
            'usage_date, query_count'
        ).eq('user_id', current_user.id).gte(
            'usage_date', start_date.isoformat()
        ).lte(
            'usage_date', end_date.isoformat()
        ).order('usage_date', desc=True).execute()
        
        return {
            "status": "success",
            "usage_history": result.data or [],
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            }
        }
    except Exception as e:
        logger.error(f"Error getting usage history: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get usage history")    


# Admin helper function
async def check_admin_access(current_user):
    """Check if user has admin access using user_roles table"""
    try:
        supabase = get_supabase_client()
        result = supabase.table('user_roles').select('role').eq('user_id', current_user.id).eq('role', 'admin').eq('is_active', True).execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=403, detail="Admin access required")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking admin access: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to verify admin access")

# ADMIN ENDPOINTS
@app.post("/api/admin/packages")
async def create_package(
    package_data: PackageCreateRequest,
    current_user = Depends(get_current_user)
):
    """Create a new subscription package (Admin only)"""
    try:
        await check_admin_access(current_user)
        
        admin_service = AdminPackageService()
        package_id = await admin_service.create_custom_package(
            current_user.id,
            package_data.dict()
        )
        return {"success": True, "package_id": package_id, "message": "Package created successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/admin/packages")
async def get_all_packages(current_user = Depends(get_current_user)):
    """Get all packages for admin dashboard"""
    try:
        await check_admin_access(current_user)
        
        admin_service = AdminPackageService()
        packages = await admin_service.get_all_packages(current_user.id)
        return {"packages": packages}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/admin/packages/{package_id}")
async def update_package(
    package_id: str,
    package_data: PackageUpdateRequest,
    current_user = Depends(get_current_user)
):
    """Update an existing package"""
    try:
        await check_admin_access(current_user)
        
        admin_service = AdminPackageService()
        success = await admin_service.update_package(
            package_id, 
            current_user.id,
            package_data.dict()
        )
        return {"success": success, "message": "Package updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/admin/packages/{package_id}")
async def delete_package(
    package_id: str,
    current_user = Depends(get_current_user)
):
    """Delete/deactivate a package"""
    try:
        await check_admin_access(current_user)
        
        admin_service = AdminPackageService()
        success = await admin_service.delete_package(package_id, current_user.id)
        return {"success": success, "message": "Package deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/admin/assign-package")
async def assign_package_to_user(
    assignment: AssignPackageRequest,
    current_user = Depends(get_current_user)
):
    """Assign a package to a user"""
    try:
        await check_admin_access(current_user)
        
        admin_service = AdminPackageService()
        success = await admin_service.assign_package_to_user(
            assignment.user_id,
            assignment.package_id,
            current_user.id
        )
        return {"success": success, "message": "Package assigned successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/admin/users/{user_id}/usage")
async def get_user_usage_stats(
    user_id: str,
    current_user = Depends(get_current_user)
):
    """Get usage statistics for a specific user"""
    try:
        await check_admin_access(current_user)
        
        subscription_service = EnhancedSubscriptionService()
        stats = await subscription_service.get_comprehensive_usage_stats(user_id)
        return stats
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# USER ENDPOINTS (for viewing packages)
@app.get("/packages")
async def get_available_packages():
    """Get available packages for users to see"""
    try:
        admin_service = AdminPackageService()
        packages = await admin_service.get_all_packages()  # No admin_user_id = only active packages
        return {"packages": packages}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/my-subscription")
async def get_my_subscription(current_user = Depends(get_current_user)):
    """Get current user's subscription details"""
    try:
        subscription_service = EnhancedSubscriptionService()
        stats = await subscription_service.get_comprehensive_usage_stats(current_user.id)
        return stats
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# PROMPT MANAGEMENT ENDPOINTS (ADMIN)
# =============================================================================

@app.get("/api/admin/prompts")
async def get_all_prompt_templates(current_user = Depends(get_current_user)):
    """Get all prompt templates for admin management"""
    try:
        # Verify admin role
        is_admin = await verify_admin_role(current_user.id)
        if not is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        templates = await prompt_management_service.get_all_prompt_templates(current_user.id)
        
        return {
            "status": "success",
            "templates": templates,
            "total": len(templates)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting prompt templates: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get prompt templates: {str(e)}")

@app.post("/api/admin/prompts")
async def create_prompt_template(
    prompt_data: PromptTemplateRequest,
    current_user = Depends(get_current_user)
):
    """Create a new prompt template"""
    try:
        # Verify admin role
        is_admin = await verify_admin_role(current_user.id)
        if not is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        template_id = await prompt_management_service.create_prompt_template(
            current_user.id, 
            prompt_data.dict()
        )
        
        return {
            "status": "success",
            "message": "Prompt template created successfully",
            "template_id": template_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating prompt template: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create prompt template: {str(e)}")

@app.get("/api/admin/prompts/categories")
async def get_prompt_categories(current_user = Depends(get_current_user)):
    """Get all available prompt categories"""
    try:
        # Verify admin role
        is_admin = await verify_admin_role(current_user.id)
        if not is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        supabase = get_supabase_client()
        
        # Check if prompt_templates table exists first
        try:
            result = supabase.table('prompt_templates').select('category').execute()
            
            if result.data:
                categories = list(set([row['category'] for row in result.data if row['category']]))
                categories.sort()
            else:
                categories = []
                
        except Exception as table_error:
            logger.error(f"Error accessing prompt_templates table: {str(table_error)}")
            # Return default categories if table doesn't exist
            categories = ['system', 'legal', 'general', 'admin']
        
        return {
            "status": "success",
            "categories": categories
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting prompt categories: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get prompt categories: {str(e)}")

@app.get("/api/admin/prompts/user-types")
async def get_prompt_user_types(current_user = Depends(get_current_user)):
    """Get all available prompt user types"""
    try:
        # Verify admin role
        is_admin = await verify_admin_role(current_user.id)
        if not is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        supabase = get_supabase_client()
        
        # Check if prompt_templates table exists first
        try:
            result = supabase.table('prompt_templates').select('user_type').execute()
            
            if result.data:
                user_types = list(set([row['user_type'] for row in result.data if row['user_type']]))
                user_types.sort()
            else:
                user_types = []
                
        except Exception as table_error:
            logger.error(f"Error accessing prompt_templates table: {str(table_error)}")
            # Return default user types if table doesn't exist
            user_types = ['all', 'admin', 'premium', 'basic']
        
        return {
            "status": "success",
            "user_types": user_types
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting prompt user types: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get prompt user types: {str(e)}")

@app.get("/api/admin/prompts/{template_id}")
async def get_prompt_template(
    template_id: str,
    current_user = Depends(get_current_user)
):
    """Get a specific prompt template by ID"""
    try:
        # Verify admin role
        is_admin = await verify_admin_role(current_user.id)
        if not is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        supabase = get_supabase_client()
        result = supabase.table('prompt_templates').select('*').eq('id', template_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Prompt template not found")
        
        return {
            "status": "success",
            "template": result.data[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting prompt template: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get prompt template: {str(e)}")

@app.put("/api/admin/prompts/{template_id}")
async def update_prompt_template(
    template_id: str,
    prompt_data: PromptTemplateUpdateRequest,
    current_user = Depends(get_current_user)
):
    """Update an existing prompt template"""
    try:
        # Verify admin role
        is_admin = await verify_admin_role(current_user.id)
        if not is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        # Only include non-None values in update
        update_data = {k: v for k, v in prompt_data.dict().items() if v is not None}
        
        success = await prompt_management_service.update_prompt_template(
            current_user.id, 
            template_id, 
            update_data
        )
        
        if success:
            return {
                "status": "success",
                "message": "Prompt template updated successfully"
            }
        else:
            raise HTTPException(status_code=404, detail="Prompt template not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating prompt template: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update prompt template: {str(e)}")

@app.delete("/api/admin/prompts/{template_id}")
async def delete_prompt_template(
    template_id: str,
    current_user = Depends(get_current_user)
):
    """Delete a prompt template (soft delete)"""
    try:
        # Verify admin role
        is_admin = await verify_admin_role(current_user.id)
        if not is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        success = await prompt_management_service.delete_prompt_template(
            current_user.id, 
            template_id
        )
        
        if success:
            return {
                "status": "success",
                "message": "Prompt template deleted successfully"
            }
        else:
            raise HTTPException(status_code=404, detail="Prompt template not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting prompt template: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete prompt template: {str(e)}")

@app.post("/api/admin/prompts/{template_id}/restore")
async def restore_prompt_template(
    template_id: str,
    current_user = Depends(get_current_user)
):
    """Restore a soft-deleted prompt template"""
    try:
        # Verify admin role
        is_admin = await verify_admin_role(current_user.id)
        if not is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        success = await prompt_management_service.restore_prompt_template(
            current_user.id, 
            template_id
        )
        
        if success:
            return {
                "status": "success",
                "message": "Prompt template restored successfully"
            }
        else:
            raise HTTPException(status_code=404, detail="Prompt template not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring prompt template: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to restore prompt template: {str(e)}")

@app.post("/api/admin/prompts/{template_id}/duplicate")
async def duplicate_prompt_template(
    template_id: str,
    request: dict,  # {"new_name": "new_template_name"}
    current_user = Depends(get_current_user)
):
    """Duplicate an existing prompt template"""
    try:
        # Verify admin role
        is_admin = await verify_admin_role(current_user.id)
        if not is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        new_name = request.get("new_name")
        if not new_name:
            raise HTTPException(status_code=400, detail="new_name is required")
        
        new_template_id = await prompt_management_service.duplicate_prompt_template(
            current_user.id, 
            template_id, 
            new_name
        )
        
        return {
            "status": "success",
            "message": "Prompt template duplicated successfully",
            "new_template_id": new_template_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error duplicating prompt template: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to duplicate prompt template: {str(e)}")

@app.get("/api/admin/prompts/{template_id}/versions")
async def get_prompt_template_versions(
    template_id: str,
    current_user = Depends(get_current_user)
):
    """Get version history for a prompt template"""
    try:
        # Verify admin role
        is_admin = await verify_admin_role(current_user.id)
        if not is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        versions = await prompt_management_service.get_prompt_template_versions(
            current_user.id, 
            template_id
        )
        
        return {
            "status": "success",
            "versions": versions,
            "total": len(versions)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting prompt template versions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get prompt template versions: {str(e)}")

@app.post("/api/admin/prompts/{template_id}/restore")
async def restore_prompt_version(
    template_id: str,
    request: dict,  # {"version_number": 2}
    current_user = Depends(get_current_user)
):
    """Restore a prompt template to a previous version"""
    try:
        # Verify admin role
        is_admin = await verify_admin_role(current_user.id)
        if not is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        version_number = request.get("version_number")
        if version_number is None:
            raise HTTPException(status_code=400, detail="version_number is required")
        
        success = await prompt_management_service.restore_prompt_version(
            current_user.id, 
            template_id, 
            version_number
        )
        
        if success:
            return {
                "status": "success",
                "message": f"Prompt template restored to version {version_number}"
            }
        else:
            raise HTTPException(status_code=404, detail="Version not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring prompt version: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to restore prompt version: {str(e)}")

@app.post("/api/admin/prompts/test")
async def test_prompt_formatting(
    request: PromptFormatRequest,
    current_user = Depends(get_current_user)
):
    """Test prompt template formatting with provided variables"""
    try:
        # Verify admin role
        is_admin = await verify_admin_role(current_user.id)
        if not is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        formatted_prompt = await prompt_management_service.format_prompt(
            request.template_name,
            request.variables,
            request.user_type
        )
        
        return {
            "status": "success",
            "formatted_prompt": formatted_prompt,
            "template_name": request.template_name,
            "variables_used": request.variables
        }
        
    except Exception as e:
        logger.error(f"Error testing prompt formatting: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to test prompt formatting: {str(e)}")

# =============================================================================
# END PROMPT MANAGEMENT ENDPOINTS
# =============================================================================


