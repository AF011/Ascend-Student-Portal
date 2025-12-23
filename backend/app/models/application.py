from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class ApplicationStatus(str, Enum):
    PENDING = "pending"
    SHORTLISTED = "shortlisted"
    REJECTED = "rejected"
    SELECTED = "selected"
    WITHDRAWN = "withdrawn"


class JobApplication(BaseModel):
    """Schema for job application"""
    job_id: str
    student_id: str
    institution_id: str
    status: ApplicationStatus = ApplicationStatus.PENDING
    applied_at: datetime
    updated_at: datetime
    
    # Optional fields for tracking
    resume_url: Optional[str] = None
    cover_letter: Optional[str] = None
    notes: Optional[str] = None
    
    class Config:
        use_enum_values = True


class JobApplicationResponse(BaseModel):
    """Response schema for job application"""
    id: str = Field(alias="_id")
    job_id: str
    student_id: str
    institution_id: str
    status: ApplicationStatus
    applied_at: datetime
    updated_at: datetime
    resume_url: Optional[str] = None
    cover_letter: Optional[str] = None
    notes: Optional[str] = None
    
    # Enriched data
    job_details: Optional[dict] = None
    
    class Config:
        populate_by_name = True
        use_enum_values = True


class JobBookmark(BaseModel):
    """Schema for bookmarked jobs"""
    job_id: str
    student_id: str
    bookmarked_at: datetime


class StudentJobStats(BaseModel):
    """Student job statistics"""
    total_applications: int
    pending_applications: int
    shortlisted: int
    selected: int
    rejected: int
    total_bookmarks: int