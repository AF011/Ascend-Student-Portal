"""
Path: backend/app/config.py

Configuration settings for Virtual CDC Platform
UPDATED: Added multi-key Groq API support + Brevo email
"""

from pydantic_settings import BaseSettings
from typing import Optional, List  # ✅ Import List here


class Settings(BaseSettings):
    # MongoDB
    MONGODB_URL: str
    DATABASE_NAME: str
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200  # 30 days
    
    @property
    def JWT_SECRET_KEY(self):
        return self.SECRET_KEY
    
    # Google OAuth
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str
    
    # App
    APP_NAME: str = "Virtual CDC - AP"
    FRONTEND_URL: str = "http://localhost:8000"
    BACKEND_URL: str = "http://localhost:8000"
    
    # ============ GROQ AI SETTINGS (Multi-Key Support) ============
    GROQ_API_KEYS: Optional[str] = None  # ✅ Made optional
    GROQ_API_KEY: Optional[str] = None   # Backward compatible fallback
    GROQ_MODEL: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    
    @property
    def groq_api_keys_list(self) -> List[str]:
        """Parse comma-separated API keys into a list."""
        if self.GROQ_API_KEYS:
            # Multi-key mode
            keys = [key.strip() for key in self.GROQ_API_KEYS.split(',') if key.strip()]
            return keys
        elif self.GROQ_API_KEY:
            # Single key fallback
            return [self.GROQ_API_KEY]
        else:
            raise ValueError("No Groq API keys configured! Set GROQ_API_KEYS or GROQ_API_KEY in .env")
    # ==============================================================    
    
    # ============ SMTP EMAIL SETTINGS (Backup/Fallback) ============
    SMTP_SERVER: Optional[str] = "smtp.gmail.com"
    SMTP_PORT: Optional[int] = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    # ================================================================
    
    # ============ EMBEDDING SETTINGS ============
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384
    TRANSFORMERS_CACHE: str = "./model_cache"
    EMBEDDING_BATCH_SIZE: int = 32
    EMBEDDING_AUTO_GENERATE: bool = True
    EMBEDDING_RETRY_ON_FAILURE: bool = True
    EMBEDDING_MAX_RETRIES: int = 3
    EMBEDDING_USE_GPU: bool = False
    EMBEDDING_WORKERS: int = 4
    # ===========================================
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()