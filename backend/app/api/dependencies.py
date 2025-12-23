from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from bson import ObjectId  # ← ADD THIS IMPORT
from app.config import settings
from app.db.mongo import get_database

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def decode_token(token: str):
    """Decode JWT and return payload"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        print(f"❌ JWT Error: {e}")  # DEBUG
        return None


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Extract user from JWT token
    """
    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user_id"
        )

    db = get_database()
    
    # ✅ FIX: Convert string to ObjectId
    try:
        user = db.users.find_one({"_id": ObjectId(user_id)})
    except Exception as e:
        print(f"❌ Error finding user: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID"
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    # Convert _id → string for consistency
    user["id"] = str(user["_id"])
    
    # ✅ Return as SimpleNamespace (acts like an object with attributes)
    from types import SimpleNamespace
    return SimpleNamespace(
        id=str(user["_id"]),
        email=user.get("email"),
        role=user.get("role"),
        full_name=user.get("full_name"),
        profile_completed=user.get("profile_completed", False),
        is_verified=user.get("is_verified", False),
        profile_picture=user.get("profile_picture")
    )

def get_db():
    db = get_database()
    if db is None:
        raise HTTPException(
            status_code=500,
            detail="Database connection error"
        )
    return db