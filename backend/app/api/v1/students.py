"""
Students API -
Path: backend/app/api/v1/students.py
"""

from fastapi import APIRouter, HTTPException, Depends, status, Body
from typing import Optional, Dict, Any
from app.db.mongo import get_database
from app.middleware.auth_middleware import get_current_user
from app.services.student_service import student_service
from app.models.students import (
    StudentProfileData,
    StudentProfileComplete,
    StudentProfileUpdate,
    AddEducationRequest,
    AddExperienceRequest,
    AddProjectRequest,
    AddSkillRequest,
    AddCertificationRequest,
    Education,
    Experience,
    Project,
    Skill,
    Certification
)
from bson import ObjectId
from datetime import datetime
import traceback

router = APIRouter(prefix="/students", tags=["Students"])


# ============================================
# PROFILE MANAGEMENT
# ============================================

@router.get("/profile")
async def get_student_profile(current_user: dict = Depends(get_current_user)):
    """Get student profile"""
    
    if current_user["role"] != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can access this endpoint"
        )
    
    try:
        profile = await student_service.get_student_profile(current_user["user_id"])
        
        if not profile:
            raise HTTPException(status_code=404, detail="User not found")
        
        return profile
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching profile: {str(e)}"
        )


@router.post("/profile/complete")
async def complete_student_profile(
    request: StudentProfileComplete,
    current_user: dict = Depends(get_current_user)
):
    """Complete student profile and generate embedding"""
    
    if current_user["role"] != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can access this endpoint"
        )
    
    try:
        # Convert Pydantic model to dict with proper serialization
        print("=" * 80)
        print("STEP 1: Converting Pydantic model to dict...")
        
        # Use mode='json' to convert enums to their values
        profile_data = request.profile_data.model_dump(mode='json')
        
        print("STEP 2: Profile data converted successfully")
        print("Profile data keys:", profile_data.keys())
        print("=" * 80)
        
        print("STEP 3: Calling student_service.complete_student_profile...")
        result = await student_service.complete_student_profile(
            current_user["user_id"],
            profile_data
        )
        
        print("STEP 4: Profile completed successfully!")
        print("=" * 80)
        
        return result
    
    except ValueError as e:
        print(f"❌ ValueError in complete_student_profile: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"❌ Exception in complete_student_profile: {e}")
        print(f"Exception type: {type(e).__name__}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error completing profile: {str(e)}"
        )


@router.put("/profile/update")
async def update_student_profile(
    request: StudentProfileUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update entire student profile and regenerate embedding"""
    
    if current_user["role"] != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can access this endpoint"
        )
    
    try:
        # Convert Pydantic model to dict with proper serialization
        profile_data = request.profile_data.model_dump(mode='json')
        
        result = await student_service.update_student_profile(
            current_user["user_id"],
            profile_data
        )
        
        return result
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating profile: {str(e)}"
        )


# ============================================
# EDUCATION MANAGEMENT
# ============================================

@router.post("/profile/education")
async def add_education(
    request: AddEducationRequest,
    current_user: dict = Depends(get_current_user)
):
    """Add education entry to profile"""
    
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Only students can access this")
    
    try:
        result = await student_service.add_to_array(
            current_user["user_id"],
            "education",
            request.education.dict()
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/profile/education/{index}")
async def update_education(
    index: int,
    education: Education,
    current_user: dict = Depends(get_current_user)
):
    """Update education entry by index"""
    
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Only students can access this")
    
    try:
        result = await student_service.update_array_item(
            current_user["user_id"],
            "education",
            index,
            education.dict()
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/profile/education/{index}")
async def delete_education(
    index: int,
    current_user: dict = Depends(get_current_user)
):
    """Delete education entry by index"""
    
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Only students can access this")
    
    try:
        result = await student_service.delete_array_item(
            current_user["user_id"],
            "education",
            index
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# EXPERIENCE MANAGEMENT
# ============================================

@router.post("/profile/experience")
async def add_experience(
    request: AddExperienceRequest,
    current_user: dict = Depends(get_current_user)
):
    """Add experience entry to profile"""
    
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Only students can access this")
    
    try:
        result = await student_service.add_to_array(
            current_user["user_id"],
            "experience",
            request.experience.dict()
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/profile/experience/{index}")
async def update_experience(
    index: int,
    experience: Experience,
    current_user: dict = Depends(get_current_user)
):
    """Update experience entry by index"""
    
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Only students can access this")
    
    try:
        result = await student_service.update_array_item(
            current_user["user_id"],
            "experience",
            index,
            experience.dict()
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/profile/experience/{index}")
async def delete_experience(
    index: int,
    current_user: dict = Depends(get_current_user)
):
    """Delete experience entry by index"""
    
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Only students can access this")
    
    try:
        result = await student_service.delete_array_item(
            current_user["user_id"],
            "experience",
            index
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# PROJECTS MANAGEMENT
# ============================================

@router.post("/profile/projects")
async def add_project(
    request: AddProjectRequest,
    current_user: dict = Depends(get_current_user)
):
    """Add project entry to profile"""
    
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Only students can access this")
    
    try:
        result = await student_service.add_to_array(
            current_user["user_id"],
            "projects",
            request.project.dict()
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/profile/projects/{index}")
async def update_project(
    index: int,
    project: Project,
    current_user: dict = Depends(get_current_user)
):
    """Update project entry by index"""
    
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Only students can access this")
    
    try:
        result = await student_service.update_array_item(
            current_user["user_id"],
            "projects",
            index,
            project.dict()
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/profile/projects/{index}")
async def delete_project(
    index: int,
    current_user: dict = Depends(get_current_user)
):
    """Delete project entry by index"""
    
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Only students can access this")
    
    try:
        result = await student_service.delete_array_item(
            current_user["user_id"],
            "projects",
            index
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# SKILLS MANAGEMENT
# ============================================

@router.post("/profile/skills")
async def add_skill(
    request: AddSkillRequest,
    current_user: dict = Depends(get_current_user)
):
    """Add skill to profile"""
    
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Only students can access this")
    
    try:
        result = await student_service.add_to_array(
            current_user["user_id"],
            "skills",
            request.skill.dict()
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/profile/skills/{index}")
async def delete_skill(
    index: int,
    current_user: dict = Depends(get_current_user)
):
    """Delete skill by index"""
    
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Only students can access this")
    
    try:
        result = await student_service.delete_array_item(
            current_user["user_id"],
            "skills",
            index
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# CERTIFICATIONS MANAGEMENT
# ============================================

@router.post("/profile/certifications")
async def add_certification(
    request: AddCertificationRequest,
    current_user: dict = Depends(get_current_user)
):
    """Add certification to profile"""
    
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Only students can access this")
    
    try:
        result = await student_service.add_to_array(
            current_user["user_id"],
            "certifications",
            request.certification.dict()
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/profile/certifications/{index}")
async def update_certification(
    index: int,
    certification: Certification,
    current_user: dict = Depends(get_current_user)
):
    """Update certification by index"""
    
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Only students can access this")
    
    try:
        result = await student_service.update_array_item(
            current_user["user_id"],
            "certifications",
            index,
            certification.dict()
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/profile/certifications/{index}")
async def delete_certification(
    index: int,
    current_user: dict = Depends(get_current_user)
):
    """Delete certification by index"""
    
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Only students can access this")
    
    try:
        result = await student_service.delete_array_item(
            current_user["user_id"],
            "certifications",
            index
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# EMBEDDING MANAGEMENT
# ============================================

@router.post("/profile/regenerate-embedding")
async def regenerate_profile_embedding(current_user: dict = Depends(get_current_user)):
    """Manually regenerate profile embedding"""
    
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Only students can access this")
    
    try:
        result = await student_service.regenerate_profile_embedding(
            current_user["user_id"]
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profile/embedding-status")
async def get_embedding_status(current_user: dict = Depends(get_current_user)):
    """Check embedding status"""
    
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Only students can access this")
    
    try:
        db = get_database()
        user = db.users.find_one(
            {"_id": ObjectId(current_user["user_id"])},
            {"profile_embedding": 1, "embedding_generated_at": 1, "embedding_model": 1}
        )
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        has_embedding = user.get("profile_embedding") is not None
        
        return {
            "has_embedding": has_embedding,
            "embedding_generated_at": user.get("embedding_generated_at"),
            "embedding_model": user.get("embedding_model"),
            "embedding_dimension": len(user.get("profile_embedding", [])) if has_embedding else 0,
            "can_get_recommendations": has_embedding
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))