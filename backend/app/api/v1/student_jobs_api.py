from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

from app.api.dependencies import get_current_user  # ✅ This returns user object
from app.db.mongo import get_database
from app.services.notification_service import notification_service
from app.models.notification import NotificationType, NotificationPriority
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/student/jobs", tags=["student-jobs"])


def get_db():
    db = get_database()
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    return db


@router.get("/recommended", response_model=dict)
async def get_recommended_jobs(
    limit: int = Query(10, ge=1, le=50),
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get job recommendations based on student profile"""
    
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can access job recommendations")
    
    # Get student profile
    student = db.students.find_one({"user_id": current_user.id})
    
    if not student or not student.get("profile_data"):
        # No profile - return recent jobs
        jobs = list(
            db.jobs.find({"is_active": True, "status": "active"})
            .sort("posted_at", -1)
            .limit(limit)
        )
    else:
        profile = student["profile_data"]
        
        # Extract student skills
        technical_skills = profile.get("technical_skills", "")
        skills_list = [s.strip().lower() for s in technical_skills.split(",") if s.strip()]
        
        # Find jobs matching student skills
        if skills_list:
            query = {
                "is_active": True,
                "status": "active",
                "$or": [
                    {"skills_required": {"$regex": "|".join(skills_list), "$options": "i"}},
                    {"description": {"$regex": "|".join(skills_list[:3]), "$options": "i"}}  # Top 3 skills
                ]
            }
            
            jobs = list(
                db.jobs.find(query)
                .sort("posted_at", -1)
                .limit(limit)
            )
        else:
            # No skills in profile - return recent jobs
            jobs = list(
                db.jobs.find({"is_active": True, "status": "active"})
                .sort("posted_at", -1)
                .limit(limit)
            )
    
    # Convert ObjectId to string
    for job in jobs:
        job["_id"] = str(job["_id"])
    
    return {
        "success": True,
        "jobs": jobs,
        "count": len(jobs)
    }


@router.post("/{job_id}/apply", response_model=dict)
async def apply_to_job(
    job_id: str,
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """Apply to a job"""
    
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can apply to jobs")
    
    # Check if job exists
    job = db.jobs.find_one({"_id": ObjectId(job_id)})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if not job.get("is_active"):
        raise HTTPException(status_code=400, detail="This job is no longer active")
    
    # Check if already applied
    existing_application = db.job_applications.find_one({
        "job_id": job_id,
        "student_id": current_user.id
    })
    
    if existing_application:
        raise HTTPException(status_code=400, detail="You have already applied to this job")
    
    # Create application
    application = {
        "job_id": job_id,
        "student_id": current_user.id,
        "institution_id": job["institution_id"],
        "status": "pending",  # pending, shortlisted, rejected, selected
        "applied_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = db.job_applications.insert_one(application)
    
    # Increment applications count
    db.jobs.update_one(
        {"_id": ObjectId(job_id)},
        {"$inc": {"applications_count": 1}}
    )
    
    logger.info(f"Student {current_user.id} applied to job {job_id}")
    
    return {
        "success": True,
        "message": "Application submitted successfully",
        "application_id": str(result.inserted_id)
    }


@router.get("/my-applications", response_model=dict)
async def get_my_applications(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = None,
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get student's job applications"""
    
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can access this endpoint")
    
    query = {"student_id": current_user.id}
    if status:
        query["status"] = status
    
    total = db.job_applications.count_documents(query)
    
    applications = list(
        db.job_applications.find(query)
        .sort("applied_at", -1)
        .skip(skip)
        .limit(limit)
    )
    
    # Enrich with job details
    for app in applications:
        app["_id"] = str(app["_id"])
        
        # Get job details
        job = db.jobs.find_one({"_id": ObjectId(app["job_id"])})
        if job:
            job["_id"] = str(job["_id"])
            app["job"] = job  # ✅ FIXED: Changed from "job_details" to "job"
    
    return {
        "success": True,
        "applications": applications,
        "total": total
    }

@router.post("/{job_id}/bookmark", response_model=dict)
async def bookmark_job(
    job_id: str,
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """Bookmark/save a job for later"""
    
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can bookmark jobs")
    
    # Check if job exists
    job = db.jobs.find_one({"_id": ObjectId(job_id)})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check if already bookmarked
    existing = db.job_bookmarks.find_one({
        "job_id": job_id,
        "student_id": current_user.id
    })
    
    if existing:
        raise HTTPException(status_code=400, detail="Job already bookmarked")
    
    # Create bookmark
    bookmark = {
        "job_id": job_id,
        "student_id": current_user.id,
        "bookmarked_at": datetime.utcnow()
    }
    
    result = db.job_bookmarks.insert_one(bookmark)
    
    logger.info(f"Student {current_user.id} bookmarked job {job_id}")
    
    return {
        "success": True,
        "message": "Job bookmarked successfully",
        "bookmark_id": str(result.inserted_id)
    }


@router.delete("/{job_id}/bookmark", response_model=dict)
async def remove_bookmark(
    job_id: str,
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """Remove bookmark from a job"""
    
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can remove bookmarks")
    
    result = db.job_bookmarks.delete_one({
        "job_id": job_id,
        "student_id": current_user.id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    
    return {
        "success": True,
        "message": "Bookmark removed successfully"
    }


@router.get("/bookmarks", response_model=dict)
async def get_bookmarked_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get student's bookmarked jobs"""
    
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can access bookmarks")
    
    query = {"student_id": current_user.id}
    
    total = db.job_bookmarks.count_documents(query)
    
    bookmarks = list(
        db.job_bookmarks.find(query)
        .sort("bookmarked_at", -1)
        .skip(skip)
        .limit(limit)
    )
    
    jobs = []
    for bookmark in bookmarks:
        # Get job details
        job = db.jobs.find_one({"_id": ObjectId(bookmark["job_id"])})
        if job:
            job["_id"] = str(job["_id"])
            job["bookmarked_at"] = bookmark["bookmarked_at"]
            jobs.append(job)
    
    return {
        "success": True,
        "jobs": jobs,
        "total": total
    }


@router.get("/{job_id}/check-status", response_model=dict)
async def check_job_interaction_status(
    job_id: str,
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """Check if student has applied to or bookmarked a job"""
    
    if current_user.role != "student":
        return {
            "success": True,
            "has_applied": False,
            "is_bookmarked": False
        }
    
    # Check application
    application = db.job_applications.find_one({
        "job_id": job_id,
        "student_id": current_user.id
    })
    
    # Check bookmark
    bookmark = db.job_bookmarks.find_one({
        "job_id": job_id,
        "student_id": current_user.id
    })
    
    application_status = None
    if application:
        application_status = application.get("status")
    
    return {
        "success": True,
        "has_applied": application is not None,
        "application_status": application_status,
        "is_bookmarked": bookmark is not None
    }


@router.get("/stats", response_model=dict)
async def get_student_job_stats(
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get student's job interaction statistics"""
    
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can access this endpoint")
    
    total_applications = db.job_applications.count_documents({"student_id": current_user.id})
    pending_applications = db.job_applications.count_documents({
        "student_id": current_user.id,
        "status": "pending"
    })
    shortlisted = db.job_applications.count_documents({
        "student_id": current_user.id,
        "status": "shortlisted"
    })
    selected = db.job_applications.count_documents({
        "student_id": current_user.id,
        "status": "selected"
    })
    rejected = db.job_applications.count_documents({
        "student_id": current_user.id,
        "status": "rejected"
    })
    
    total_bookmarks = db.job_bookmarks.count_documents({"student_id": current_user.id})
    
    return {
        "success": True,
        "stats": {
            "total_applications": total_applications,
            "pending_applications": pending_applications,
            "shortlisted": shortlisted,
            "selected": selected,
            "rejected": rejected,
            "total_bookmarks": total_bookmarks
        }
    }



"""
============================================================================
ADD THIS CODE TO: backend/app/api/v1/student_jobs_api.py

LOCATION: At the END of the file (after get_student_job_stats function)

This adds 3 new AI-powered recommendation endpoints using MongoDB Vector Search
============================================================================
"""


# ========================================================================
# 🎯 AI-POWERED JOB RECOMMENDATIONS (MongoDB Vector Search)
# ========================================================================

@router.get("/for-me", response_model=dict)
async def get_personalized_jobs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    min_score: int = Query(80, ge=0, le=100, description="Minimum match score (0-100)"),  # ✅ Changed from 60 to 80
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    🎯 AI-Powered Personalized Job Recommendations
    
    Only shows HIGH-QUALITY matches (80%+ similarity by default).
    If no good matches exist, returns empty list with helpful message.
    """
    
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can access personalized recommendations")
    
    try:
        from app.services.recommendation_service import recommendation_service
        
        # Get personalized recommendations with HIGH threshold
        result = await recommendation_service.get_jobs_for_student(
            student_id=current_user.id,
            page=page,
            limit=limit,
            min_score=min_score / 100.0  # Convert 80 to 0.80
        )
        
        if "error" in result:
            error_msg = result["error"]
            
            if "profile embedding not found" in error_msg.lower():
                return {
                    "success": False,
                    "message": "Please complete your profile to get personalized recommendations",
                    "has_quality_matches": False,
                    "jobs": [],
                    "pagination": {
                        "page": 1,
                        "limit": limit,
                        "total_count": 0,
                        "total_pages": 0,
                        "has_next": False,
                        "has_prev": False
                    }
                }
            
            raise HTTPException(status_code=500, detail=error_msg)
        
        # ✅ NEW: Check if we have quality matches
        has_quality_matches = len(result['jobs']) > 0
        
        logger.info(f"Returned {len(result['jobs'])} high-quality jobs (>={min_score}%) for student {current_user.id}")
        
        return {
            "success": True,
            "message": "AI-powered recommendations based on your profile" if has_quality_matches else "No high-quality matches found",
            "has_quality_matches": has_quality_matches,  # ✅ NEW FIELD
            "min_score_threshold": min_score,  # ✅ Tell frontend what threshold was used
            "jobs": result["jobs"],
            "pagination": result["pagination"],
            "total": result["pagination"]["total_count"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting personalized jobs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {str(e)}")


@router.get("/top-matches", response_model=dict)
async def get_top_job_matches(
    limit: int = Query(10, ge=1, le=50, description="Number of top matches"),
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    🏆 Get Top N Best Matching Jobs
    
    Returns the highest-scoring job matches for the student.
    Perfect for dashboard "Top Recommendations" widget.
    
    Parameters:
    - limit: Number of top matches to return (default 10, max 50)
    
    NOTE: Requires student profile to be completed and embeddings generated
    """
    
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can access top matches")
    
    try:
        # Import recommendation service
        from app.services.recommendation_service import recommendation_service
        
        # Get top matches
        result = await recommendation_service.get_top_matches(
            student_id=current_user.id,
            limit=limit
        )
        
        # Handle errors
        if "error" in result:
            error_msg = result["error"]
            
            # If profile not completed, return empty results
            if "profile embedding not found" in error_msg.lower():
                logger.warning(f"Student {current_user.id} profile incomplete - no top matches")
                return {
                    "success": False,
                    "message": "Please complete your profile to get top matches",
                    "jobs": [],
                    "count": 0
                }
            
            # Other errors
            logger.error(f"Error getting top matches: {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
        
        logger.info(f"Returned {result['total']} top matches for student {current_user.id}")
        
        return {
            "success": True,
            "message": f"Top {result['total']} job matches for you",
            "jobs": result["jobs"],
            "count": result["total"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting top matches: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get top matches: {str(e)}")


@router.get("/recommendation-status", response_model=dict)
async def check_recommendation_readiness(
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    ✅ Check Recommendation System Readiness
    
    Checks if personalized recommendations are ready for the student.
    
    Returns:
    - profile_completed: Whether student has completed their profile
    - has_embedding: Whether profile embedding has been generated  
    - vector_search_ready: Whether MongoDB Vector Search is configured
    - can_get_recommendations: Whether student can get personalized recommendations
    
    Use this endpoint to show helpful messages in the UI
    """
    
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can check recommendation status")
    
    try:
        # Check student profile and embeddings
        user = db.users.find_one({"_id": ObjectId(current_user.id)})
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        profile_completed = user.get("profile_completed", False)
        has_embedding = user.get("profile_embedding") is not None
        embedding_generated_at = user.get("embedding_generated_at")
        embedding_model = user.get("embedding_model", "all-MiniLM-L6-v2")
        
        # Check vector search status
        from app.services.recommendation_service import recommendation_service
        vector_status = await recommendation_service.check_vector_search_status()
        vector_search_ready = vector_status.get("status") == "ready"
        
        # Can get recommendations if all conditions met
        can_get_recommendations = profile_completed and has_embedding and vector_search_ready
        
        # Build helpful message
        if can_get_recommendations:
            message = "✅ You can get personalized recommendations!"
        elif not profile_completed:
            message = "⚠️ Please complete your profile first"
        elif not has_embedding:
            message = "⚠️ Profile embeddings are being generated..."
        elif not vector_search_ready:
            message = "⚠️ Recommendation system is being set up..."
        else:
            message = "⚠️ Recommendations not available yet"
        
        logger.info(f"Recommendation status check for student {current_user.id}: can_get={can_get_recommendations}")
        
        return {
            "success": True,
            "profile_completed": profile_completed,
            "has_embedding": has_embedding,
            "embedding_generated_at": embedding_generated_at,
            "embedding_model": embedding_model,
            "vector_search_ready": vector_search_ready,
            "vector_search_status": vector_status,
            "can_get_recommendations": can_get_recommendations,
            "message": message
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking recommendation status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))