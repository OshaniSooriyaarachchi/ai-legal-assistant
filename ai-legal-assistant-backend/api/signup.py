from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from config.supabase_client import get_supabase_client
from config.settings import settings
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class SignupRequest(BaseModel):
    email: EmailStr
    password: str

@router.post("/api/auth/signup", response_model=dict)
async def signup(data: SignupRequest, req: Request):
    """
    Signup endpoint that sends a verification email and only creates the account if the email is verified.
    """
    supabase = get_supabase_client()
    # 1. Create user with email/password, but require email confirmation
    try:
        # Basic validation: enforce stronger password policy (min 8 chars)
        if not data.password or len(data.password) < 8:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")

        # Determine redirect URL from request Origin if it's in allowed origins
        redirect_base = None
        try:
            allowed = set(settings.get_allowed_origins_list() or [])
            origin = req.headers.get("origin")
            if origin and origin in allowed:
                redirect_base = origin
        except Exception:
            redirect_base = None

        payload = {
            "email": data.email,
            "password": data.password,
        }
        # Only include options if we have a valid redirect_base
        if redirect_base:
            payload["options"] = {"email_redirect_to": f"{redirect_base}/auth/callback"}

        response = supabase.auth.sign_up(payload)
        if not response.user:
            raise HTTPException(status_code=400, detail="Signup failed")
        # 2. Supabase will send a verification email automatically
        # 3. User must verify email before being able to login
        return {"status": "success", "message": "Verification email sent. Please verify your email to activate your account."}
    except Exception as e:
        logger.error(f"Signup failed for {data.email}: {repr(e)}")
        raise HTTPException(status_code=400, detail=f"Signup failed: {str(e)}")
