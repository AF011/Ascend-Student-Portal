from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from app.services.embedding_service import embedding_service
from app.models.job import JobCreate, JobUpdate, JobResponse, JobStatus
from app.api.dependencies import get_current_user
from app.db.mongo import get_database
from app.services.notification_service import notification_service
from app.models.notification import NotificationType, NotificationPriority
import logging


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


def get_db():
    db = get_database()
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    return db


@router.post("", response_model=dict)
async def create_job(
    job: JobCreate,
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """Create a new job posting (Institution only)"""
    
    # Only institutions can post jobs
    if current_user.role != "institution":
        raise HTTPException(status_code=403, detail="Only institutions can post jobs")
    
    # ✅ Get institution profile from users collection
    user_doc = db.users.find_one({"_id": ObjectId(current_user.id)})
    
    if not user_doc:
        raise HTTPException(status_code=400, detail="User not found")
    
    # Get institution name from profile
    institution_name = "Unknown Institution"
    
    if "profile_data" in user_doc and isinstance(user_doc["profile_data"], dict):
        institution_name = user_doc["profile_data"].get("institution_name", "Unknown Institution")
    elif "institution_name" in user_doc:
        institution_name = user_doc.get("institution_name", "Unknown Institution")
    
    if institution_name == "Unknown Institution":
        raise HTTPException(status_code=400, detail="Please complete your institution profile first")
        
    
    # Create job document
    job_dict = job.dict()
    job_dict["institution_id"] = current_user.id
    job_dict["institution_name"] = institution_name
    job_dict["is_active"] = True
    job_dict["status"] = JobStatus.ACTIVE.value
    job_dict["posted_at"] = datetime.utcnow()
    job_dict["updated_at"] = datetime.utcnow()
    job_dict["applications_count"] = 0
    job_dict["views_count"] = 0
    
    # Embedding fields (will be generated immediately)
    job_dict["job_embedding"] = None
    job_dict["embedding_generated_at"] = None
    job_dict["embedding_model"] = "all-MiniLM-L6-v2"
    
    # Insert into database
    result = db.jobs.insert_one(job_dict)
    job_id = str(result.inserted_id)
    
    logger.info(f"Job created: {job_id} by institution {current_user.id}")
    
    # ✅ GENERATE EMBEDDING IMMEDIATELY
    try:
        embedding = await embedding_service.generate_job_embedding(
            title=job.title,
            description=job.description,
            skills=job.skills_required or "",
            requirements=job.requirements or ""
        )
        
        if embedding:
            db.jobs.update_one(
                {"_id": ObjectId(job_id)},
                {
                    "$set": {
                        "job_embedding": embedding,
                        "embedding_generated_at": datetime.utcnow(),
                        "embedding_model": "all-MiniLM-L6-v2"
                    }
                }
            )            
        else:
            logger.error(f"⚠️ Failed to generate embedding for job {job_id}")    
    except Exception as e:
        logger.error(f"Embedding generation error: {e}")        
    
    # Send notifications to all students
    try:
        await notification_service.notify_new_job_posted(
            job_id=job_id,
            job_title=job.title,
            company_name=job.company,
            institution_id=current_user.id
        )        
    except Exception as e:
        logger.error(f"Failed to send notifications: {e}")        
    
    return {
        "success": True,
        "message": "Job posted successfully",
        "job_id": job_id
    }

@router.get("", response_model=dict)
async def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    job_type: Optional[str] = None,
    location: Optional[str] = None,
    company: Optional[str] = None,
    search: Optional[str] = None,
    active_only: bool = True,
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """List all jobs with filters"""
    
    # Build query
    query = {}
    
    if active_only:
        query["is_active"] = True
        query["status"] = JobStatus.ACTIVE.value
    
    if job_type:
        query["job_type"] = job_type
    
    if location:
        query["location"] = {"$regex": location, "$options": "i"}
    
    if company:
        query["company"] = {"$regex": company, "$options": "i"}
    
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"skills_required": {"$regex": search, "$options": "i"}}
        ]
    
    # Get total count
    total = db.jobs.count_documents(query)
    
    # Get jobs
    jobs = list(
        db.jobs.find(query)
        .sort("posted_at", -1)
        .skip(skip)
        .limit(limit)
    )
    
    # Convert to response format
    job_responses = []
    for job in jobs:
        job["_id"] = str(job["_id"])
        job_responses.append(job)
    
    return {
        "success": True,
        "jobs": job_responses,
        "total": total,
        "page": skip // limit + 1,
        "page_size": limit
    }


@router.get("/my-jobs", response_model=dict)
async def get_my_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get jobs posted by current institution"""
    
    if current_user.role != "institution":
        raise HTTPException(status_code=403, detail="Only institutions can access this endpoint")
    
    query = {"institution_id": current_user.id}
    
    total = db.jobs.count_documents(query)
    
    jobs = list(
        db.jobs.find(query)
        .sort("posted_at", -1)
        .skip(skip)
        .limit(limit)
    )
    
    for job in jobs:
        job["_id"] = str(job["_id"])
    
    return {
        "success": True,
        "jobs": jobs,
        "total": total
    }


@router.get("/{job_id}", response_model=dict)
async def get_job(
    job_id: str,
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get job details by ID"""
    
    job = db.jobs.find_one({"_id": ObjectId(job_id)})
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Increment views count
    db.jobs.update_one(
        {"_id": ObjectId(job_id)},
        {"$inc": {"views_count": 1}}
    )
    
    job["_id"] = str(job["_id"])
    job["views_count"] += 1
    
    return {
        "success": True,
        "job": job
    }


@router.put("/{job_id}", response_model=dict)
async def update_job(
    job_id: str,
    job_update: JobUpdate,
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """Update a job (Institution owner only)"""
    
    # Check if job exists and belongs to current institution
    job = db.jobs.find_one({"_id": ObjectId(job_id)})
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job["institution_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="You don't have permission to update this job")
    
    # Prepare update data
    update_data = {k: v for k, v in job_update.dict().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    
    # Update job
    db.jobs.update_one(
        {"_id": ObjectId(job_id)},
        {"$set": update_data}
    )
    
    logger.info(f"Job updated: {job_id}")
    
    return {
        "success": True,
        "message": "Job updated successfully"
    }


@router.delete("/{job_id}", response_model=dict)
async def delete_job(
    job_id: str,
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """Delete a job (Institution owner only)"""
    
    # Check if job exists and belongs to current institution
    job = db.jobs.find_one({"_id": ObjectId(job_id)})
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job["institution_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="You don't have permission to delete this job")
    
    # Soft delete - mark as inactive
    db.jobs.update_one(
        {"_id": ObjectId(job_id)},
        {
            "$set": {
                "is_active": False,
                "status": JobStatus.CLOSED.value,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    logger.info(f"Job deleted: {job_id}")
    
    return {
        "success": True,
        "message": "Job deleted successfully"
    }


@router.post("/{job_id}/toggle-status", response_model=dict)
async def toggle_job_status(
    job_id: str,
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """Toggle job active status"""
    
    job = db.jobs.find_one({"_id": ObjectId(job_id)})
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job["institution_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    new_status = not job.get("is_active", True)
    new_status_enum = JobStatus.ACTIVE if new_status else JobStatus.CLOSED
    
    db.jobs.update_one(
        {"_id": ObjectId(job_id)},
        {
            "$set": {
                "is_active": new_status,
                "status": new_status_enum.value,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return {
        "success": True,
        "message": f"Job {'activated' if new_status else 'deactivated'} successfully",
        "is_active": new_status
    }


@router.get("/stats/overview", response_model=dict)
async def get_job_stats(
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get job statistics for institution"""
    
    if current_user.role != "institution":
        raise HTTPException(status_code=403, detail="Only institutions can access this endpoint")
    
    total_jobs = db.jobs.count_documents({"institution_id": current_user.id})
    active_jobs = db.jobs.count_documents({
        "institution_id": current_user.id,
        "is_active": True
    })
    
    # Get total views and applications
    pipeline = [
        {"$match": {"institution_id": current_user.id}},
        {"$group": {
            "_id": None,
            "total_views": {"$sum": "$views_count"},
            "total_applications": {"$sum": "$applications_count"}
        }}
    ]
    
    stats = list(db.jobs.aggregate(pipeline))
    
    return {
        "success": True,
        "stats": {
            "total_jobs": total_jobs,
            "active_jobs": active_jobs,
            "closed_jobs": total_jobs - active_jobs,
            "total_views": stats[0]["total_views"] if stats else 0,
            "total_applications": stats[0]["total_applications"] if stats else 0
        }
    }

@router.get("/{job_id}/applicants", response_model=dict)
async def get_job_applicants(
    job_id: str,
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get all applicants for a job (Institution only)"""
    
    if current_user.role != "institution":
        raise HTTPException(status_code=403, detail="Only institutions can view applicants")
    
    # Verify job belongs to institution
    job = db.jobs.find_one({"_id": ObjectId(job_id)})
    if not job or job["institution_id"] != current_user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get applications
    applications = list(db.job_applications.find({"job_id": job_id}))
    
    # Add student data
    applicants_data = []
    for app in applications:
        student = db.users.find_one({"_id": ObjectId(app["student_id"])})
        applicants_data.append({
            "_id": str(app["_id"]),
            "student_name": student.get("full_name", "N/A") if student else "N/A",
            "student_email": student.get("email", "N/A") if student else "N/A",
            "applied_at": app["applied_at"],
            "status": app.get("status", "pending")
        })
    
    applicants_data.sort(key=lambda x: x["applied_at"], reverse=True)
    
    return {
        "success": True,
        "applicants": applicants_data
    }

# ADD THIS TO jobs_api.py (after get_job_applicants endpoint)

@router.put("/applications/{application_id}/status", response_model=dict)
async def update_application_status(
    application_id: str,
    request: dict,
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """Update application status and send email notification (Institution only)"""
    
    if current_user.role != "institution":
        raise HTTPException(status_code=403, detail="Only institutions can update status")
    
    new_status = request.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="Status is required")
    
    valid_statuses = ["pending", "shortlisted", "selected", "rejected", "withdrawn"]
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
    
    # Get application
    application = db.job_applications.find_one({"_id": ObjectId(application_id)})
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Verify job belongs to institution
    job = db.jobs.find_one({"_id": ObjectId(application["job_id"])})
    if not job or job["institution_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Update status
    db.job_applications.update_one(
        {"_id": ObjectId(application_id)},
        {"$set": {"status": new_status, "updated_at": datetime.utcnow()}}
    )
    
    
    # Create in-app notification
    try:
        status_messages = {
            "shortlisted": "Congratulations! You've been shortlisted",
            "selected": "🎉 Congratulations! You've been selected",
            "rejected": "Application status updated",
        }
        
        await notification_service.create_notification(
            user_id=application["student_id"],
            type=NotificationType.APPLICATION_STATUS.value,
            title=status_messages.get(new_status, "Application Status Updated"),
            message=f"Your application for {job['title']} at {job['company']} has been {new_status}",
            priority=NotificationPriority.HIGH.value if new_status == "selected" else NotificationPriority.MEDIUM.value,
            related_job_id=application["job_id"]
        )
    except Exception as e:
        logger.error(f"Failed to create notification: {e}")
    
    return {
        "success": True,
        "message": "Status updated and notification sent",
        "new_status": new_status
    }
