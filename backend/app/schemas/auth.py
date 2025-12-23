from pydantic import BaseModel, EmailStr
from typing import Optional
from app.models.user import UserRole


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[UserRole] = None


class GoogleAuthRequest(BaseModel):
    code: str
    #role: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict
    message: str