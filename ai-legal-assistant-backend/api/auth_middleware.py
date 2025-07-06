from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config.supabase_client import get_supabase_client

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validate JWT token and return current user"""
    try:
        supabase = get_supabase_client()
        
        # Verify JWT token
        response = supabase.auth.get_user(credentials.credentials)
        
        if not response.user:
            raise HTTPException(status_code=401, detail="Invalid authentication")
        
        return response.user
        
    except Exception as e:
        raise HTTPException(status_code=401, detail="Authentication failed")

async def require_admin_role(current_user = Depends(get_current_user)):
    """Require admin role for protected endpoints"""
    from services.admin_service import AdminService
    
    admin_service = AdminService()
    is_admin = await admin_service.verify_admin_role(current_user.id)
    
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    return current_user