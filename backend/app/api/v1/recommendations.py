"""
Path: backend/app/api/v1/recommendations.py

Recommendations API - Fetch personalized job recommendations
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from app.middleware.auth_middleware import get_current_user, require_student
from app.services.recommendation_service import recommendation_service
from app.db.mongo import get_database
from bson import ObjectId
from datetime import datetime

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.get("/top-matches")
async def get_top_matches(
    limit: int = Query(default=20, ge=1, le=100),
    min_score: int = Query(default=60, ge=0, le=100),
    current_user: dict = Depends(require_student)
):
    """
    Get personalized top job matches for logged-in student
    
    Returns ALL recommendations sorted by score (not just top 5)
    """
    try:
        db = get_database()
        student_id = current_user["user_id"]
        
        # Get recommendations from DB
        recommendations = list(db.recommendations.find({
            "student_id": student_id,
            "final_score": {"$gte": min_score}
        }).sort("final_score", -1).limit(limit))
        
        if not recommendations:
            return {
                "message": "No recommendations found. Profile may need completion or jobs may not be available.",
                "total_recommendations": 0,
                "recommendations": []
            }
        
        # Fetch job details for each recommendation
        enriched_recommendations = []
        
        for rec in recommendations:
            job = db.jobs.find_one({"_id": ObjectId(rec["job_id"])})
            
            if job:
                enriched_recommendations.append({
                    "recommendation_id": str(rec["_id"]),
                    "final_score": rec["final_score"],
                    "match_category": rec["match_category"],
                    "similarity_score": rec["similarity_score"],
                    "total_boost": rec["total_boost"],
                    "recommended_at": rec["recommended_at"],
                    "is_bookmarked": rec.get("is_bookmarked", False),
                    "is_applied": rec.get("is_applied", False),
                    "job": {
                        "id": str(job["_id"]),
                        "title": job["title"],
                        "company": job["company"],
                        "location": job["location"],
                        "job_type": job["job_type"],
                        "description": job.get("description", "")[:300] + "...",
                        "skills_required": job.get("skills_required", ""),
                        "salary_range": job.get("salary_range", ""),
                        "experience_required": job.get("experience_required", ""),
                        "posted_at": job["posted_at"],
                        "source": job.get("source", "unknown"),
                        "job_url": job.get("job_url", "")
                    }
                })
        
        return {
            "total_recommendations": len(enriched_recommendations),
            "showing": len(enriched_recommendations),
            "min_score_filter": min_score,
            "recommendations": enriched_recommendations
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching recommendations: {str(e)}"
        )


@router.get("/by-category/{category}")
async def get_recommendations_by_category(
    category: str,
    limit: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(require_student)
):
    """
    Get recommendations by match category
    Categories: perfect_match, good_fit, worth_considering
    """
    try:
        db = get_database()
        student_id = current_user["user_id"]
        
        valid_categories = ["perfect_match", "good_fit", "worth_considering"]
        
        if category not in valid_categories:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category. Must be one of: {', '.join(valid_categories)}"
            )
        
        recommendations = list(db.recommendations.find({
            "student_id": student_id,
            "match_category": category
        }).sort("final_score", -1).limit(limit))
        
        # Enrich with job details
        enriched_recommendations = []
        
        for rec in recommendations:
            job = db.jobs.find_one({"_id": ObjectId(rec["job_id"])})
            
            if job:
                enriched_recommendations.append({
                    "recommendation_id": str(rec["_id"]),
                    "final_score": rec["final_score"],
                    "match_category": rec["match_category"],
                    "recommended_at": rec["recommended_at"],
                    "job": {
                        "id": str(job["_id"]),
                        "title": job["title"],
                        "company": job["company"],
                        "location": job["location"],
                        "job_type": job["job_type"],
                        "description": job.get("description", "")[:300] + "...",
                        "salary_range": job.get("salary_range", ""),
                        "posted_at": job["posted_at"],
                        "source": job.get("source", "unknown")
                    }
                })
        
        return {
            "category": category,
            "total": len(enriched_recommendations),
            "recommendations": enriched_recommendations
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching recommendations: {str(e)}"
        )


@router.post("/generate")
async def generate_my_recommendations(
    current_user: dict = Depends(require_student)
):
    """
    Manually trigger recommendation generation for current student
    Useful when profile is updated or user wants fresh recommendations
    """
    try:
        student_id = current_user["user_id"]
        
        result = await recommendation_service.generate_recommendations_for_student(student_id)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Save to DB
        recommendations = result.get("recommendations", [])
        saved = await recommendation_service.save_recommendations_to_db(student_id, recommendations)
        
        return {
            "message": "Recommendations generated successfully",
            "total_recommendations": saved,
            "generated_at": datetime.utcnow()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating recommendations: {str(e)}"
        )


@router.get("/stats")
async def get_recommendation_stats(
    current_user: dict = Depends(require_student)
):
    """
    Get recommendation statistics for current student
    """
    try:
        db = get_database()
        student_id = current_user["user_id"]
        
        # Count by category
        perfect_match_count = db.recommendations.count_documents({
            "student_id": student_id,
            "match_category": "perfect_match"
        })
        
        good_fit_count = db.recommendations.count_documents({
            "student_id": student_id,
            "match_category": "good_fit"
        })
        
        worth_considering_count = db.recommendations.count_documents({
            "student_id": student_id,
            "match_category": "worth_considering"
        })
        
        total_count = perfect_match_count + good_fit_count + worth_considering_count
        
        # Get latest recommendation date
        latest_rec = db.recommendations.find_one(
            {"student_id": student_id},
            sort=[("recommended_at", -1)]
        )
        
        return {
            "total_recommendations": total_count,
            "by_category": {
                "perfect_match": perfect_match_count,
                "good_fit": good_fit_count,
                "worth_considering": worth_considering_count
            },
            "last_generated_at": latest_rec.get("recommended_at") if latest_rec else None
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching stats: {str(e)}"
        )


@router.post("/bookmark/{job_id}")
async def bookmark_job(
    job_id: str,
    current_user: dict = Depends(require_student)
):
    """Bookmark a recommended job"""
    try:
        db = get_database()
        student_id = current_user["user_id"]
        
        result = db.recommendations.update_one(
            {
                "student_id": student_id,
                "job_id": job_id
            },
            {
                "$set": {
                    "is_bookmarked": True,
                    "bookmarked_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        
        return {"message": "Job bookmarked successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error bookmarking job: {str(e)}"
        )


@router.delete("/bookmark/{job_id}")
async def remove_bookmark(
    job_id: str,
    current_user: dict = Depends(require_student)
):
    """Remove bookmark from a job"""
    try:
        db = get_database()
        student_id = current_user["user_id"]
        
        result = db.recommendations.update_one(
            {
                "student_id": student_id,
                "job_id": job_id
            },
            {
                "$set": {
                    "is_bookmarked": False,
                    "bookmarked_at": None
                }
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        
        return {"message": "Bookmark removed successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error removing bookmark: {str(e)}"
        )


@router.post("/mark-applied/{job_id}")
async def mark_job_applied(
    job_id: str,
    current_user: dict = Depends(require_student)
):
    """Mark a job as applied"""
    try:
        db = get_database()
        student_id = current_user["user_id"]
        
        result = db.recommendations.update_one(
            {
                "student_id": student_id,
                "job_id": job_id
            },
            {
                "$set": {
                    "is_applied": True,
                    "applied_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        
        # Also increment application count on job
        db.jobs.update_one(
            {"_id": ObjectId(job_id)},
            {"$inc": {"applications_count": 1}}
        )
        
        return {"message": "Job marked as applied successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error marking job as applied: {str(e)}"
        )