from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.utils.jwt_handler import verify_token

security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token and return current user"""
    
    token = credentials.credentials
    
    payload = verify_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {
        "email": payload.get("sub"),
        "role": payload.get("role"),
        "user_id": payload.get("user_id")
    }


async def require_student(current_user: dict = Depends(get_current_user)):
    """Require user to be a student"""
    if current_user["role"] != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only accessible to students"
        )
    return current_user


async def require_institution(current_user: dict = Depends(get_current_user)):
    """Require user to be an institution"""
    if current_user["role"] != "institution":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only accessible to institutions"
        )
    return current_user