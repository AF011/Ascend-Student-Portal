from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    STUDENT = "student"
    INSTITUTION = "institution"
    ADMIN = "admin"


class UserBase(BaseModel):
    email: EmailStr
    role: UserRole
    full_name: Optional[str] = None
    profile_picture: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False


class UserInDB(UserBase):
    id: str = Field(alias="_id")
    google_id: Optional[str] = None
    profile_completed: bool = False
    profile_data: Optional[Dict[str, Any]] = None
    
    # ============ NEW EMBEDDING FIELDS ============
    profile_embedding: Optional[List[float]] = None  # 384-dim vector for sentence-transformers
    embedding_generated_at: Optional[datetime] = None
    embedding_model: Optional[str] = "all-MiniLM-L6-v2"  # Track which model generated the embedding
    # ==============================================
    
    created_at: datetime
    updated_at: datetime
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "email": "student@example.com",
                "role": "student",
                "full_name": "John Doe",
                "google_id": "1234567890",
                "profile_completed": False,
                "is_active": True,
                "is_verified": True,
                "profile_embedding": None,
                "embedding_generated_at": None,
                "embedding_model": "all-MiniLM-L6-v2"
            }
        }


class UserCreate(BaseModel):
    email: EmailStr
    role: UserRole
    full_name: Optional[str] = None
    google_id: Optional[str] = None
    profile_picture: Optional[str] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    profile_picture: Optional[str] = None
    profile_data: Optional[Dict[str, Any]] = None
    profile_completed: Optional[bool] = None


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    role: UserRole
    full_name: Optional[str] = None
    profile_picture: Optional[str] = None
    profile_completed: bool
    is_active: bool
    is_verified: bool
    created_at: datetime
    
    # ============ NEW EMBEDDING FIELDS (Optional in response) ============
    has_embedding: bool = False  # Flag to indicate if embedding exists
    embedding_generated_at: Optional[datetime] = None
    # =====================================================================