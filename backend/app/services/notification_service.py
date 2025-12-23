from datetime import datetime
from typing import List, Optional, Dict, Any
from bson import ObjectId
from app.db.mongo import get_database
from app.models.notification import NotificationType, NotificationPriority
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing notifications"""
    
    def get_database(self):
        db = get_database()
        if db is None:
            raise Exception("Database not connected")
        return db
    
    async def create_notification(
        self,
        user_id: str,
        type: NotificationType,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        related_job_id: Optional[str] = None,
        related_institution_id: Optional[str] = None,
        action_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        send_email: bool = True
    ) -> str:
        """Create a new notification"""
        db = self.get_database()
        
        notification = {
            "user_id": user_id,
            "type": type.value if isinstance(type, NotificationType) else type,
            "title": title,
            "message": message,
            "priority": priority.value if isinstance(priority, NotificationPriority) else priority,
            "related_job_id": related_job_id,
            "related_institution_id": related_institution_id,
            "action_url": action_url,
            "metadata": metadata or {},
            "is_read": False,
            "is_email_sent": False,
            "created_at": datetime.utcnow(),
            "read_at": None
        }
        
        result = db.notifications.insert_one(notification)
        notification_id = str(result.inserted_id)
        
        logger.info(f"Created notification {notification_id} for user {user_id}")
        
        # Send email notification if requested
        if send_email:
            try:
                await self.send_email_notification(notification_id, user_id, title, message, action_url)
            except Exception as e:
                logger.error(f"Failed to send email notification: {e}")
        
        return notification_id
    
    async def create_bulk_notifications(
        self,
        user_ids: List[str],
        type: NotificationType,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        related_job_id: Optional[str] = None,
        related_institution_id: Optional[str] = None,
        action_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        send_email: bool = True
    ) -> List[str]:
        """Create notifications for multiple users"""
        db = self.get_database()
        
        notifications = []
        for user_id in user_ids:
            notification = {
                "user_id": user_id,
                "type": type.value if isinstance(type, NotificationType) else type,
                "title": title,
                "message": message,
                "priority": priority.value if isinstance(priority, NotificationPriority) else priority,
                "related_job_id": related_job_id,
                "related_institution_id": related_institution_id,
                "action_url": action_url,
                "metadata": metadata or {},
                "is_read": False,
                "is_email_sent": False,
                "created_at": datetime.utcnow(),
                "read_at": None
            }
            notifications.append(notification)
        
        if notifications:
            result = db.notifications.insert_many(notifications)
            notification_ids = [str(id) for id in result.inserted_ids]
            
            logger.info(f"Created {len(notification_ids)} bulk notifications")
            
            # Send email notifications
            if send_email:
                for user_id in user_ids:
                    try:
                        await self.send_email_notification(None, user_id, title, message, action_url)
                    except Exception as e:
                        logger.error(f"Failed to send email to {user_id}: {e}")
            
            return notification_ids
        
        return []
    
    async def get_user_notifications(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
        unread_only: bool = False
    ) -> tuple[List[Dict], int]:
        """Get notifications for a user"""
        db = self.get_database()
        
        query = {"user_id": user_id}
        if unread_only:
            query["is_read"] = False
        
        total = db.notifications.count_documents(query)
        
        notifications = list(
            db.notifications.find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
        
        # Convert ObjectId to string
        for notif in notifications:
            notif["_id"] = str(notif["_id"])
            if notif.get("related_job_id"):
                notif["related_job_id"] = str(notif["related_job_id"])
            if notif.get("related_institution_id"):
                notif["related_institution_id"] = str(notif["related_institution_id"])
        
        return notifications, total
    
    async def get_unread_count(self, user_id: str) -> int:
        """Get count of unread notifications"""
        db = self.get_database()
        return db.notifications.count_documents({"user_id": user_id, "is_read": False})
    
    async def mark_as_read(self, notification_ids: List[str], user_id: str) -> int:
        """Mark notifications as read"""
        db = self.get_database()
        
        result = db.notifications.update_many(
            {
                "_id": {"$in": [ObjectId(id) for id in notification_ids]},
                "user_id": user_id
            },
            {
                "$set": {
                    "is_read": True,
                    "read_at": datetime.utcnow()
                }
            }
        )
        
        logger.info(f"Marked {result.modified_count} notifications as read for user {user_id}")
        return result.modified_count
    
    async def mark_all_as_read(self, user_id: str) -> int:
        """Mark all user's notifications as read"""
        db = self.get_database()
        
        result = db.notifications.update_many(
            {"user_id": user_id, "is_read": False},
            {
                "$set": {
                    "is_read": True,
                    "read_at": datetime.utcnow()
                }
            }
        )
        
        logger.info(f"Marked all notifications as read for user {user_id}")
        return result.modified_count
    
    async def delete_notification(self, notification_id: str, user_id: str) -> bool:
        """Delete a notification"""
        db = self.get_database()
        
        result = db.notifications.delete_one({
            "_id": ObjectId(notification_id),
            "user_id": user_id
        })
        
        return result.deleted_count > 0
    
    async def get_notification_stats(self, user_id: str) -> Dict[str, Any]:
        """Get notification statistics for a user"""
        db = self.get_database()
        
        total = db.notifications.count_documents({"user_id": user_id})
        unread = db.notifications.count_documents({"user_id": user_id, "is_read": False})
        
        # Count by type
        by_type = {}
        for type_value in ["job_posted", "job_updated", "job_deadline", "system", "announcement"]:
            count = db.notifications.count_documents({"user_id": user_id, "type": type_value})
            by_type[type_value] = count
        
        # Count by priority
        by_priority = {}
        for priority in ["low", "medium", "high", "urgent"]:
            count = db.notifications.count_documents({"user_id": user_id, "priority": priority})
            by_priority[priority] = count
        
        return {
            "total": total,
            "unread": unread,
            "by_type": by_type,
            "by_priority": by_priority
        }
    
    async def send_email_notification(
        self,
        notification_id: Optional[str],
        user_id: str,
        title: str,
        message: str,
        action_url: Optional[str] = None
    ):
        """Send email notification (to be implemented with email service)"""
        # Import here to avoid circular dependency
        try:
            from app.services.email_service import send_notification_email
            
            # Get user email
            db = self.get_database()
            user = db.users.find_one({"_id": ObjectId(user_id)})
            
            if user and user.get("email"):
                await send_notification_email(
                    to_email=user["email"],
                    subject=title,
                    message=message,
                    action_url=action_url
                )
                
                # Mark email as sent
                if notification_id:
                    db.notifications.update_one(
                        {"_id": ObjectId(notification_id)},
                        {"$set": {"is_email_sent": True}}
                    )
                
                logger.info(f"Email sent to {user['email']}")
        except Exception as e:
            logger.error(f"Error sending email: {e}")
    
    async def notify_new_job_posted(
        self,
        job_id: str,
        job_title: str,
        company_name: str,
        institution_id: str,
        target_student_ids: Optional[List[str]] = None
    ):
        """Send notifications when a new job is posted"""
        db = self.get_database()
        
        # If no specific students, notify all active students
        if not target_student_ids:
            students = db.users.find({"role": "student", "is_active": True})
            target_student_ids = [str(s["_id"]) for s in students]
        
        title = f"New Job: {job_title}"
        message = f"{company_name} has posted a new job opportunity. Check it out!"
        action_url = f"/student/jobs/{job_id}"
        
        await self.create_bulk_notifications(
            user_ids=target_student_ids,
            type=NotificationType.JOB_POSTED,
            title=title,
            message=message,
            priority=NotificationPriority.MEDIUM,
            related_job_id=job_id,
            related_institution_id=institution_id,
            action_url=action_url,
            send_email=True
        )


# Singleton instance
notification_service = NotificationService()