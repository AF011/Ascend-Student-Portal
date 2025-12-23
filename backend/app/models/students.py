"""
Student Profile Models
Path: backend/app/models/students.py

Defines structured schema for student profile data with nested models
for education, experience, projects, skills, certifications, etc.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import date
from enum import Enum


# ============================================
# ENUMS
# ============================================

class EducationLevel(str, Enum):
    TENTH = "10th"
    TWELFTH = "12th"
    UG = "UG"
    PG = "PG"
    PHD = "PhD"


class SkillProficiency(str, Enum):
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    EXPERT = "Expert"


class EmploymentType(str, Enum):
    INTERNSHIP = "Internship"
    FULL_TIME = "Full-time"
    PART_TIME = "Part-time"
    CONTRACT = "Contract"
    FREELANCE = "Freelance"


class WorkMode(str, Enum):
    REMOTE = "Remote"
    ONSITE = "Onsite"
    HYBRID = "Hybrid"


# ============================================
# SUB-MODELS
# ============================================

class Education(BaseModel):
    """Education entry (10th, 12th, UG, PG)"""
    level: EducationLevel
    board_university: str = Field(..., min_length=1, max_length=200)
    school_college: str = Field(..., min_length=1, max_length=200)
    year: int = Field(..., ge=1990, le=2030)
    percentage_cgpa: float = Field(..., ge=0, le=100)
    
    # Optional fields for higher education
    degree: Optional[str] = Field(None, max_length=100)  # "B.Tech", "M.Tech", etc.
    branch: Optional[str] = Field(None, max_length=100)  # "CSE", "ECE", etc.
    
    class Config:
        json_schema_extra = {
            "example": {
                "level": "UG",
                "board_university": "APJ Abdul Kalam Technological University",
                "school_college": "IIT Delhi",
                "year": 2025,
                "percentage_cgpa": 8.5,
                "degree": "B.Tech",
                "branch": "Computer Science"
            }
        }


class Skill(BaseModel):
    """Skill with proficiency level"""
    name: str = Field(..., min_length=1, max_length=50)
    proficiency: SkillProficiency
    category: Optional[str] = Field(None, max_length=50)  # "Programming", "Framework", etc.
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Python",
                "proficiency": "Expert",
                "category": "Programming Language"
            }
        }


class Experience(BaseModel):
    """Work experience entry"""
    company: str = Field(..., min_length=1, max_length=200)
    role: str = Field(..., min_length=1, max_length=100)
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}$")  # "YYYY-MM"
    end_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}$")
    is_current: bool = False
    description: str = Field(..., min_length=10, max_length=2000)
    location: Optional[str] = Field(None, max_length=100)
    
    class Config:
        json_schema_extra = {
            "example": {
                "company": "Google",
                "role": "Software Engineering Intern",
                "start_date": "2023-06",
                "end_date": "2023-08",
                "is_current": False,
                "description": "Worked on React frontend for Google Cloud Console",
                "location": "Remote"
            }
        }


class Project(BaseModel):
    """Project entry"""
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=10, max_length=2000)
    tech_stack: List[str] = Field(..., min_items=1)
    link: Optional[str] = Field(None, max_length=500)
    github_link: Optional[str] = Field(None, max_length=500)
    start_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}$")
    end_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}$")
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "E-commerce Platform",
                "description": "Full-stack MERN e-commerce with payment integration",
                "tech_stack": ["React", "Node.js", "MongoDB", "Stripe"],
                "link": "https://myproject.com",
                "github_link": "https://github.com/user/project",
                "start_date": "2024-01",
                "end_date": "2024-03"
            }
        }


class Certification(BaseModel):
    """Certification entry"""
    name: str = Field(..., min_length=1, max_length=200)
    issuer: str = Field(..., min_length=1, max_length=200)
    issue_date: str = Field(..., pattern=r"^\d{4}-\d{2}$")  # "YYYY-MM"
    expiry_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}$")
    credential_id: Optional[str] = Field(None, max_length=100)
    credential_url: Optional[str] = Field(None, max_length=500)
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "AWS Certified Developer - Associate",
                "issuer": "Amazon Web Services",
                "issue_date": "2024-05",
                "credential_id": "AWS-12345",
                "credential_url": "https://aws.amazon.com/verification/12345"
            }
        }


class SocialLinks(BaseModel):
    """Social media and portfolio links"""
    linkedin: Optional[str] = Field(None, max_length=500)
    github: Optional[str] = Field(None, max_length=500)
    portfolio: Optional[str] = Field(None, max_length=500)
    resume_link: Optional[str] = Field(None, max_length=500)
    twitter: Optional[str] = Field(None, max_length=500)
    leetcode: Optional[str] = Field(None, max_length=500)
    
    class Config:
        json_schema_extra = {
            "example": {
                "linkedin": "https://linkedin.com/in/johndoe",
                "github": "https://github.com/johndoe",
                "portfolio": "https://johndoe.dev",
                "resume_link": "https://drive.google.com/resume.pdf"
            }
        }


class CareerPreferences(BaseModel):
    """Career preferences and expectations"""
    employment_type: List[EmploymentType] = Field(default_factory=list)
    work_mode: List[WorkMode] = Field(default_factory=list)
    preferred_roles: Optional[str] = Field(None, max_length=500)
    preferred_industries: Optional[str] = Field(None, max_length=500)
    expected_salary: Optional[str] = Field(None, max_length=100)
    willing_to_relocate: Optional[str] = Field(None, max_length=20)  # "Yes", "No", "Maybe"
    notice_period: Optional[str] = Field(None, max_length=100)
    availability_date: Optional[date] = None
    preferred_locations: Optional[str] = Field(None, max_length=500)
    
    class Config:
        json_schema_extra = {
            "example": {
                "employment_type": ["Full-time", "Internship"],
                "work_mode": ["Remote", "Hybrid"],
                "preferred_roles": "Full Stack Developer, Backend Engineer",
                "preferred_industries": "Technology, Fintech, E-commerce",
                "expected_salary": "5-8 LPA",
                "willing_to_relocate": "Yes",
                "notice_period": "After Graduation",
                "availability_date": "2025-06-01",
                "preferred_locations": "Bangalore, Hyderabad, Remote"
            }
        }


# ============================================
# MAIN PROFILE MODEL
# ============================================

class StudentProfileData(BaseModel):
    """Complete student profile data structure"""
    
    # ========== PERSONAL INFORMATION ==========
    full_name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., pattern=r"^\+?[0-9]{10,15}$")
    location: str = Field(..., min_length=1, max_length=200)
    gender: Optional[str] = Field(None, max_length=20)
    date_of_birth: Optional[date] = None
    
    # ========== EDUCATION ==========
    education: List[Education] = Field(default_factory=list)
    
    # ========== SKILLS ==========
    skills: List[Skill] = Field(default_factory=list)
    domain_expertise: Optional[str] = Field(None, max_length=200)
    languages: Optional[str] = Field(None, max_length=500)  # "English, Hindi, Telugu"
    
    # ========== EXPERIENCE ==========
    experience: List[Experience] = Field(default_factory=list)
    total_experience_years: int = Field(default=0, ge=0, le=50)
    current_role: str = Field(default="Student", max_length=100)
    current_company: Optional[str] = Field(None, max_length=200)
    
    # ========== PROJECTS ==========
    projects: List[Project] = Field(default_factory=list)
    
    # ========== CERTIFICATIONS ==========
    certifications: List[Certification] = Field(default_factory=list)
    
    # ========== CAREER PREFERENCES ==========
    preferences: CareerPreferences = Field(default_factory=CareerPreferences)
    
    # ========== LINKS ==========
    links: SocialLinks = Field(default_factory=SocialLinks)
    
    # ========== ADDITIONAL ==========
    summary: Optional[str] = Field(None, max_length=2000)
    achievements: Optional[str] = Field(None, max_length=2000)
    
    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "John Doe",
                "phone": "+919876543210",
                "location": "Bangalore, Karnataka",
                "gender": "Male",
                "education": [
                    {
                        "level": "UG",
                        "board_university": "APJ Abdul Kalam University",
                        "school_college": "IIT Delhi",
                        "year": 2025,
                        "percentage_cgpa": 8.5,
                        "degree": "B.Tech",
                        "branch": "Computer Science"
                    }
                ],
                "skills": [
                    {"name": "Python", "proficiency": "Expert", "category": "Programming"},
                    {"name": "React", "proficiency": "Intermediate", "category": "Framework"}
                ],
                "domain_expertise": "Full Stack Development",
                "total_experience_years": 0,
                "current_role": "Student"
            }
        }


# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

class StudentProfileComplete(BaseModel):
    """Request model for completing profile"""
    profile_data: StudentProfileData


class StudentProfileUpdate(BaseModel):
    """Request model for updating profile"""
    profile_data: StudentProfileData


class AddEducationRequest(BaseModel):
    """Request to add education entry"""
    education: Education


class AddExperienceRequest(BaseModel):
    """Request to add experience entry"""
    experience: Experience


class AddProjectRequest(BaseModel):
    """Request to add project entry"""
    project: Project


class AddSkillRequest(BaseModel):
    """Request to add skill"""
    skill: Skill


class AddCertificationRequest(BaseModel):
    """Request to add certification"""
    certification: Certification