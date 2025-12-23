from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from app.schemas.auth import GoogleAuthRequest, LoginResponse
from app.services.auth_service import AuthService
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/google/login")
async def google_login():
    """Generate Google OAuth login URL."""
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={settings.GOOGLE_CLIENT_ID}&"
        f"redirect_uri={settings.GOOGLE_REDIRECT_URI}&"
        f"response_type=code&"
        f"scope=openid email profile&"
        f"access_type=offline&"
        f"prompt=consent"
        # No state parameter needed
    )

    return {"auth_url": google_auth_url}


# ----------------------------------------------------------
# 🔥 POST CALLBACK — Receives code from frontend JavaScript
# ----------------------------------------------------------
@router.post("/oauth_callback", response_model=LoginResponse)
async def google_callback(request: GoogleAuthRequest):
    """Handle Google OAuth callback with automatic role detection based on email domain."""
    
    code = request.code
    
    # Exchange code for tokens
    token_data = await AuthService.exchange_code_for_token(code)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange authorization code"
        )
    
    # Get user info from Google
    google_user = await AuthService.get_google_user_info(token_data["access_token"])
    if not google_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to fetch Google user info"
        )
    
    # 🔥 AUTO-DETECT ROLE FROM EMAIL DOMAIN
    email = google_user.get("email", "").lower()  # Convert to lowercase for safety
    
    if email.endswith("@gmail.com"):
        role = "student"
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid email domain. Please use @gmail.com for students"
        )
    
    # Create or get user with auto-detected role
    user = await AuthService.create_or_get_user(google_user, role)
    
    # Generate JWT + response
    response = AuthService.generate_auth_response(user)
    
    return response

@router.get("/test")
async def test_auth():
    """Simple route to verify auth is functional."""
    return {
        "message": "Auth routes working!",
        "client_id_preview": settings.GOOGLE_CLIENT_ID[:10] + "...",
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
    }