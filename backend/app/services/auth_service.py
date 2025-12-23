from datetime import datetime
from typing import Optional, Dict
import httpx
from authlib.integrations.starlette_client import OAuth
from app.config import settings
from app.db.mongo import get_database
from app.models.user import UserCreate, UserRole
from app.utils.jwt_handler import create_access_token
from bson import ObjectId


class AuthService:

    @staticmethod
    async def get_google_user_info(access_token: str) -> Optional[Dict]:
        """Get user info from Google"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if response.status_code == 200:
                return response.json()
            return None

    @staticmethod
    async def exchange_code_for_token(code: str) -> Optional[Dict]:
        """Exchange authorization code for access token"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code"
                }
            )

            if response.status_code == 200:
                return response.json()
            return None

    @staticmethod
    async def create_or_get_user(google_user: Dict, role) -> Dict:
        """
        Create new user or get existing user.
        role can be either UserRole enum or a string like "student"
        """

        # 🔥 FIX: Ensure role becomes string ("student" / "institution")
        if isinstance(role, UserRole):
            role_value = role.value
        else:
            role_value = str(role)

        db = get_database()

        # Check if user exists
        existing_user = db.users.find_one({"email": google_user["email"]})

        if existing_user:
            # Update last login
            db.users.update_one(
                {"_id": existing_user["_id"]},
                {"$set": {"updated_at": datetime.utcnow()}}
            )
            existing_user["id"] = str(existing_user["_id"])
            return existing_user

        # Create new user
        new_user = {
            "email": google_user["email"],
            "role": role_value,
            "full_name": google_user.get("name"),
            "profile_picture": google_user.get("picture"),
            "google_id": google_user.get("id"),
            "is_active": True,
            "is_verified": True,  # Google users are pre-verified
            "profile_completed": False,
            "profile_data": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        result = db.users.insert_one(new_user)
        new_user["_id"] = result.inserted_id
        new_user["id"] = str(result.inserted_id)

        return new_user

    @staticmethod
    def generate_auth_response(user: Dict) -> Dict:
        """Generate authentication response with JWT token"""
        token_data = {
            "sub": user["email"],
            "role": user["role"],
            "user_id": str(user["_id"])
        }

        access_token = create_access_token(token_data)

        user_response = {
            "id": str(user["_id"]),
            "email": user["email"],
            "role": user["role"],
            "full_name": user.get("full_name"),
            "profile_picture": user.get("profile_picture"),
            "profile_completed": user.get("profile_completed", False),
            "is_verified": user.get("is_verified", False)
        }

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user_response,
            "message": "Login successful"
        }
