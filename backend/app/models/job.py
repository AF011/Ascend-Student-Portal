from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class JobType(str, Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    INTERNSHIP = "internship"
    CONTRACT = "contract"
    FREELANCE = "freelance"


class JobStatus(str, Enum):
    ACTIVE = "active"
    CLOSED = "closed"
    DRAFT = "draft"


class JobBase(BaseModel):
    title: str
    company: str
    description: str
    requirements: Optional[str] = None
    skills_required: Optional[str] = None
    location: str
    job_type: JobType
    experience_required: Optional[str] = None
    salary_range: Optional[str] = None
    application_deadline: Optional[datetime] = None
    is_active: bool = True
    status: JobStatus = JobStatus.ACTIVE


class JobInDB(JobBase):
    id: str = Field(alias="_id")
    institution_id: str  # Reference to the institution that posted the job
    
    # ============ EMBEDDING FIELDS ============
    job_embedding: Optional[List[float]] = None  # 384-dim vector
    embedding_generated_at: Optional[datetime] = None
    embedding_model: Optional[str] = "all-MiniLM-L6-v2"
    # ==========================================
    
    posted_at: datetime
    updated_at: datetime
    applications_count: int = 0
    views_count: int = 0
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "title": "Software Engineer Intern",
                "company": "Tech Corp",
                "description": "Looking for talented interns...",
                "location": "Bangalore, India",
                "job_type": "internship",
                "is_active": True,
                "status": "active",
                "institution_id": "507f1f77bcf86cd799439012",
                "job_embedding": None,
                "embedding_generated_at": None
            }
        }


class JobCreate(BaseModel):
    title: str
    company: str
    description: str
    requirements: Optional[str] = None
    skills_required: Optional[str] = None
    location: str
    job_type: JobType
    experience_required: Optional[str] = None
    salary_range: Optional[str] = None
    application_deadline: Optional[datetime] = None


class JobUpdate(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    skills_required: Optional[str] = None
    location: Optional[str] = None
    job_type: Optional[JobType] = None
    experience_required: Optional[str] = None
    salary_range: Optional[str] = None
    application_deadline: Optional[datetime] = None
    is_active: Optional[bool] = None
    status: Optional[JobStatus] = None


class JobResponse(BaseModel):
    id: str
    title: str
    company: str
    description: str
    requirements: Optional[str] = None
    skills_required: Optional[str] = None
    location: str
    job_type: JobType
    experience_required: Optional[str] = None
    salary_range: Optional[str] = None
    application_deadline: Optional[datetime] = None
    is_active: bool
    status: JobStatus
    institution_id: str
    posted_at: datetime
    updated_at: datetime
    applications_count: int = 0
    views_count: int = 0
    
    # Embedding metadata (not the actual vector)
    has_embedding: bool = False
    embedding_generated_at: Optional[datetime] = None


class JobWithMatch(JobResponse):
    """Job response with similarity match score"""
    similarity_score: float
    match_percentage: float