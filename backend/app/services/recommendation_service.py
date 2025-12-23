"""
Path: backend/app/services/recommendation_service.py

MongoDB Vector Search Based Job Recommendation Engine

Features:
- Real-time score calculation (not stored)
- Semantic matching using embeddings
- Pagination support
- Filtering by minimum score
- Fast (<1 second for 200+ jobs)

Author: Virtual CDC Team
Date: December 2024
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from app.db.mongo import get_database
from bson import ObjectId

logger = logging.getLogger(__name__)


class RecommendationService:
    """
    MongoDB Vector Search based job recommendation engine
    
    Uses cosine similarity between student profile embeddings and job embeddings
    to find the best matching jobs for each student.
    
    Scores are calculated in real-time, not stored in database.
    """
    
    def __init__(self):
        self.db = None
        self.vector_index_name = "job_vector_index"  # MongoDB Atlas index name
    
    def _get_db(self):
        """Get database connection"""
        if self.db is None:
            self.db = get_database()
        return self.db
    
    async def get_jobs_for_student(
        self,
        student_id: str,
        page: int = 1,
        limit: int = 20,
        min_score: float = 0.6
    ) -> Dict:
        """
        Get paginated personalized job recommendations for a student
        
        Args:
            student_id: MongoDB ObjectId of student
            page: Page number (1-indexed)
            limit: Jobs per page (max 100)
            min_score: Minimum similarity score (0.0 to 1.0)
            
        Returns:
            {
                "jobs": [...],  # List of jobs with match scores
                "pagination": {
                    "page": 1,
                    "limit": 20,
                    "total_count": 156,
                    "total_pages": 8,
                    "has_next": True,
                    "has_prev": False
                },
                "student_branch": "CSE",
                "matching_strategy": "mongodb_vector_search"
            }
        """
        try:
            db = self._get_db()
            
            # Get student profile
            student = db.users.find_one({"_id": ObjectId(student_id)})
            
            if not student:
                return {"error": "Student not found"}
            
            # Check if student has profile embedding
            student_embedding = student.get("profile_embedding")
            if not student_embedding:
                return {
                    "error": "Profile embedding not found. Please complete your profile first.",
                    "profile_completed": student.get("profile_completed", False)
                }
            
            student_data = student.get("profile_data", {})
            student_branch = student_data.get("branch", "Unknown")
            
            # Calculate number of candidates to search
            # Search more candidates to ensure we have enough after filtering
            num_candidates = max(200, limit * 10)
            
            logger.info(f"Getting jobs for student {student_id}, page {page}, limit {limit}")
            
            # MongoDB Vector Search Pipeline
            pipeline = [
                # STEP 1: Vector Search - MongoDB does the heavy lifting!
                {
                    "$vectorSearch": {
                        "index": self.vector_index_name,
                        "path": "job_embedding",
                        "queryVector": student_embedding,  # Student profile embedding
                        "numCandidates": num_candidates,   # Search pool
                        "limit": limit * 5                 # Get more for pagination
                    }
                },
                
                # STEP 2: Add similarity score
                {
                    "$addFields": {
                        "similarity_score": {"$meta": "vectorSearchScore"}
                    }
                },
                
                # STEP 3: Filter by active status, job status, and minimum score
                # NOTE: Using $match AFTER $vectorSearch (not filter inside)
                {
                    "$match": {
                        "is_active": True,
                        "status": "active",
                        "similarity_score": {"$gte": min_score}
                    }
                },
                
                # STEP 4: Sort by score (highest first)
                {
                    "$sort": {"similarity_score": -1}
                },
                
                # STEP 5: Calculate match percentage
                {
                    "$addFields": {
                        "match_score": {
                            "$toInt": {
                                "$multiply": ["$similarity_score", 100]
                            }
                        }
                    }
                },
                
                # STEP 6: Project only needed fields
                {
                    "$project": {
                        "_id": 1,
                        "title": 1,
                        "company": 1,
                        "location": 1,
                        "description": 1,
                        "job_type": 1,
                        "salary_range": 1,
                        "experience_required": 1,
                        "skills_required": 1,
                        "source": 1,
                        "job_url": 1,
                        "posted_at": 1,
                        "similarity_score": 1,
                        "match_score": 1
                    }
                }
            ]
            
            # Execute aggregation
            all_results = list(db.jobs.aggregate(pipeline))
            
            total_count = len(all_results)
            total_pages = (total_count + limit - 1) // limit if total_count > 0 else 0
            
            # Paginate results
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            paginated_results = all_results[start_idx:end_idx]
            
            # Format jobs for response
            formatted_jobs = []
            for job in paginated_results:
                formatted_jobs.append({
                    "id": str(job["_id"]),
                    "title": job["title"],
                    "company": job["company"],
                    "location": job["location"],
                    "description": job.get("description", "")[:300] + "...",
                    "job_type": job["job_type"],
                    "salary_range": job.get("salary_range", "Not specified"),
                    "experience_required": job.get("experience_required", ""),
                    "skills_required": job.get("skills_required", ""),
                    "source": job.get("source", "unknown"),
                    "job_url": job.get("job_url", ""),
                    "posted_at": job.get("posted_at"),
                    "match_score": job["match_score"],
                    "similarity": round(job["similarity_score"], 3)
                })
            
            logger.info(f"Found {total_count} jobs for student, returning page {page} ({len(formatted_jobs)} jobs)")
            
            return {
                "jobs": formatted_jobs,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total_count": total_count,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                },
                "student_branch": student_branch,
                "matching_strategy": "mongodb_vector_search"
            }
        
        except Exception as e:
            logger.error(f"Error getting jobs for student: {str(e)}")
            return {"error": str(e)}
    
    async def get_top_matches(
        self,
        student_id: str,
        limit: int = 10
    ) -> Dict:
        """
        Get top N best matching jobs (for dashboard widget)
        
        Args:
            student_id: MongoDB ObjectId of student
            limit: Number of top jobs to return
            
        Returns:
            {
                "jobs": [...],  # List of top matching jobs
                "total": 10
            }
        """
        try:
            db = self._get_db()
            
            # Get student profile
            student = db.users.find_one({"_id": ObjectId(student_id)})
            
            if not student:
                return {"error": "Student not found"}
            
            student_embedding = student.get("profile_embedding")
            if not student_embedding:
                return {"error": "Profile embedding not found"}
            
            logger.info(f"Getting top {limit} matches for student {student_id}")
            
            # Simple vector search for top matches
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": self.vector_index_name,
                        "path": "job_embedding",
                        "queryVector": student_embedding,
                        "numCandidates": 100,
                        "limit": limit
                    }
                },
                {
                    "$addFields": {
                        "similarity_score": {"$meta": "vectorSearchScore"}
                    }
                },
                {
                    "$match": {
                        "is_active": True,
                        "status": "active"
                    }
                },
                {
                    "$addFields": {
                        "match_score": {
                            "$toInt": {
                                "$multiply": ["$similarity_score", 100]
                            }
                        }
                    }
                },
                {
                    "$project": {
                        "_id": 1,
                        "title": 1,
                        "company": 1,
                        "location": 1,
                        "job_type": 1,
                        "match_score": 1,
                        "posted_at": 1
                    }
                }
            ]
            
            results = list(db.jobs.aggregate(pipeline))
            
            formatted_jobs = []
            for job in results:
                formatted_jobs.append({
                    "id": str(job["_id"]),
                    "title": job["title"],
                    "company": job["company"],
                    "location": job["location"],
                    "job_type": job["job_type"],
                    "match_score": job["match_score"],
                    "posted_at": job.get("posted_at")
                })
            
            logger.info(f"Found {len(formatted_jobs)} top matches")
            
            return {
                "jobs": formatted_jobs,
                "total": len(formatted_jobs)
            }
        
        except Exception as e:
            logger.error(f"Error getting top matches: {str(e)}")
            return {"error": str(e)}
    
    async def check_vector_search_status(self) -> Dict:
        """
        Check if MongoDB Vector Search is ready
        
        Returns:
            {
                "status": "ready" | "not_ready" | "error",
                "message": "...",
                "index_name": "job_vector_index"
            }
        """
        try:
            db = self._get_db()
            
            # Try a simple vector search
            test_embedding = [0.1] * 384  # Dummy embedding
            
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": self.vector_index_name,
                        "path": "job_embedding",
                        "queryVector": test_embedding,
                        "numCandidates": 1,
                        "limit": 1
                    }
                },
                {"$limit": 1}
            ]
            
            list(db.jobs.aggregate(pipeline))
            
            return {
                "status": "ready",
                "message": "✅ Vector Search is working!",
                "index_name": self.vector_index_name
            }
        
        except Exception as e:
            error_msg = str(e)
            
            if "index" in error_msg.lower():
                return {
                    "status": "not_ready",
                    "message": "Vector search index not found or not ready",
                    "index_name": self.vector_index_name,
                    "error": error_msg
                }
            else:
                return {
                    "status": "error",
                    "message": "Error checking vector search status",
                    "error": error_msg
                }


# Singleton instance
recommendation_service = RecommendationService()