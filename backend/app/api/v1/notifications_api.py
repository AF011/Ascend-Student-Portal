from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from app.models.user import UserInDB
from app.api.dependencies import get_current_user
from app.services.notification_service import notification_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=dict)
async def get_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    unread_only: bool = False,
    current_user: UserInDB = Depends(get_current_user)
):
    """Get user notifications"""
    
    try:
        notifications, total = await notification_service.get_user_notifications(
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            unread_only=unread_only
        )
        
        unread_count = await notification_service.get_unread_count(current_user.id)
        
        return {
            "success": True,
            "notifications": notifications,
            "total": total,
            "unread_count": unread_count
        }
    except Exception as e:
        logger.error(f"Error getting notifications: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unread-count", response_model=dict)
async def get_unread_count(
    current_user: UserInDB = Depends(get_current_user)
):
    """Get count of unread notifications"""
    
    try:
        count = await notification_service.get_unread_count(current_user.id)
        
        return {
            "success": True,
            "unread_count": count
        }
    except Exception as e:
        logger.error(f"Error getting unread count: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/mark-read", response_model=dict)
async def mark_notifications_read(
    notification_ids: List[str],
    current_user: UserInDB = Depends(get_current_user)
):
    """Mark specific notifications as read"""
    
    try:
        count = await notification_service.mark_as_read(notification_ids, current_user.id)
        
        return {
            "success": True,
            "message": f"Marked {count} notification(s) as read",
            "count": count
        }
    except Exception as e:
        logger.error(f"Error marking notifications as read: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/mark-all-read", response_model=dict)
async def mark_all_notifications_read(
    current_user: UserInDB = Depends(get_current_user)
):
    """Mark all user notifications as read"""
    
    try:
        count = await notification_service.mark_all_as_read(current_user.id)
        
        return {
            "success": True,
            "message": "Marked all notifications as read",
            "count": count
        }
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{notification_id}", response_model=dict)
async def delete_notification(
    notification_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """Delete a notification"""
    
    try:
        success = await notification_service.delete_notification(notification_id, current_user.id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        return {
            "success": True,
            "message": "Notification deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=dict)
async def get_notification_stats(
    current_user: UserInDB = Depends(get_current_user)
):
    """Get notification statistics"""
    
    try:
        stats = await notification_service.get_notification_stats(current_user.id)
        
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error getting notification stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
