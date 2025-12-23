from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class NotificationType(str, Enum):
    JOB_POSTED = "job_posted"
    JOB_UPDATED = "job_updated"
    JOB_DEADLINE = "job_deadline"
    APPLICATION_STATUS = "application_status"
    SYSTEM = "system"
    ANNOUNCEMENT = "announcement"


class NotificationPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class NotificationBase(BaseModel):
    user_id: str
    type: NotificationType
    title: str
    message: str
    priority: NotificationPriority = NotificationPriority.MEDIUM
    
    # Optional metadata
    related_job_id: Optional[str] = None
    related_institution_id: Optional[str] = None
    action_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}


class NotificationInDB(NotificationBase):
    id: str = Field(alias="_id")
    is_read: bool = False
    is_email_sent: bool = False
    created_at: datetime
    read_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "user_id": "507f1f77bcf86cd799439012",
                "type": "job_posted",
                "title": "New Job Opportunity",
                "message": "A new Software Engineer position has been posted at Tech Corp",
                "priority": "medium",
                "related_job_id": "507f1f77bcf86cd799439013",
                "action_url": "/student/jobs/507f1f77bcf86cd799439013",
                "is_read": False,
                "created_at": "2025-01-15T10:30:00"
            }
        }


class NotificationCreate(BaseModel):
    """Schema for creating a notification"""
    user_id: str
    type: NotificationType
    title: str
    message: str
    priority: NotificationPriority = NotificationPriority.MEDIUM
    related_job_id: Optional[str] = None
    related_institution_id: Optional[str] = None
    action_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}


class NotificationResponse(BaseModel):
    """Schema for notification response"""
    id: str
    user_id: str
    type: NotificationType
    title: str
    message: str
    priority: NotificationPriority
    related_job_id: Optional[str] = None
    related_institution_id: Optional[str] = None
    action_url: Optional[str] = None
    metadata: Dict[str, Any]
    is_read: bool
    is_email_sent: bool
    created_at: datetime
    read_at: Optional[datetime] = None


class NotificationListResponse(BaseModel):
    """Schema for notification list response"""
    success: bool
    notifications: list[NotificationResponse]
    total: int
    unread_count: int


class NotificationMarkRead(BaseModel):
    """Schema for marking notification as read"""
    notification_ids: list[str]


class NotificationStats(BaseModel):
    """Notification statistics"""
    total: int
    unread: int
    by_type: Dict[str, int]
    by_priority: Dict[str, int]