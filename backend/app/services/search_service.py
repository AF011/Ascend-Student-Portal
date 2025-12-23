"""
Path: backend/app/services/search_service.py

MongoDB Vector Search Service - Direct Atlas Vector Search
No manual cosine similarity, uses MongoDB native $vectorSearch
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime
from app.db.mongo import get_database
from app.services.embedding_service import embedding_service
from bson import ObjectId

logger = logging.getLogger(__name__)


class SearchService:
    """MongoDB Atlas Vector Search for semantic job search"""
    
    def __init__(self):
        self.db = None
        self.vector_index_name = "job_vector_index"
    
    def _get_db(self):
        """Get database connection"""
        if self.db is None:
            self.db = get_database()
        return self.db
    
    async def semantic_job_search(
        self, 
        query: str,
        limit: int = 50,
        min_score: float = 0.5
    ) -> Dict:
        """
        Semantic search using MongoDB Atlas Vector Search
        
        Args:
            query: User's search query (e.g., "python backend developer bangalore")
            limit: Number of results to return
            min_score: Minimum similarity score (0.0 to 1.0)
            
        Returns:
            Dict with search results and metadata
        """
        try:
            db = self._get_db()
            
            logger.info(f"Semantic search query: '{query}'")
            
            # 1. Generate embedding for search query (direct text)
            query_embedding = await embedding_service.generate_text_embedding(query)
            
            logger.info(f"Generated query embedding: {len(query_embedding)} dimensions")
            
            # 2. MongoDB Vector Search using $vectorSearch
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": self.vector_index_name,
                        "path": "job_embedding",
                        "queryVector": query_embedding,
                        "numCandidates": limit * 4,
                        "limit": limit
                    }
                },
                {
                    "$addFields": {
                        "search_score": {"$meta": "vectorSearchScore"}
                    }
                },
                {
                    "$match": {
                        "is_active": True,
                        "status": "active",
                        "search_score": {"$gte": min_score}
                    }
                },
                {
                    "$project": {
                        "_id": 1,
                        "title": 1,
                        "company": 1,
                        "location": 1,
                        "description": 1,
                        "skills_required": 1,
                        "job_type": 1,
                        "experience_required": 1,
                        "salary_range": 1,
                        "posted_at": 1,
                        "source": 1,
                        "job_url": 1,
                        "search_score": 1
                    }
                }
            ]
            
            results = list(db.jobs.aggregate(pipeline))
            
            logger.info(f"Found {len(results)} results for query: '{query}'")
            
            # 3. Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "id": str(result["_id"]),
                    "title": result["title"],
                    "company": result["company"],
                    "location": result["location"],
                    "description": result.get("description", "")[:300] + "...",
                    "skills_required": result.get("skills_required", ""),
                    "job_type": result["job_type"],
                    "experience_required": result.get("experience_required", ""),
                    "salary_range": result.get("salary_range", ""),
                    "posted_at": result["posted_at"],
                    "source": result.get("source", "unknown"),
                    "job_url": result.get("job_url", ""),
                    "match_score": int(result["search_score"] * 100),
                    "similarity": round(result["search_score"], 3)
                })
            
            return {
                "query": query,
                "total_results": len(formatted_results),
                "results": formatted_results
            }
        
        except Exception as e:
            logger.error(f"Error in semantic search: {str(e)}")
            return {
                "error": str(e),
                "query": query,
                "total_results": 0,
                "results": []
            }
    
    async def search_jobs_for_student(
        self,
        student_id: str,
        query: str,
        limit: int = 50
    ) -> Dict:
        """
        Personalized semantic search using student profile + query
        Combines student profile embedding with query for better results
        """
        try:
            db = self._get_db()
            
            # Get student profile
            student = db.users.find_one({"_id": ObjectId(student_id)})
            
            if not student or not student.get('profile_data'):
                # Fall back to regular search
                return await self.semantic_job_search(query, limit)
            
            profile_data = student.get('profile_data', {})
            
            # Enhance query with student context
            enhanced_query = f"{query} {profile_data.get('technical_skills', '')} {profile_data.get('branch', '')}"
            
            # Generate embedding for enhanced query
            query_data = {
                "description": enhanced_query,
                "title": query,
                "skills": profile_data.get('technical_skills', '')
            }

            query_embedding = await embedding_service.generate_text_embedding(query_data)
            
            # MongoDB Vector Search
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": self.vector_index_name,
                        "path": "job_embedding",
                        "queryVector": query_embedding,
                        "numCandidates": limit * 4,
                        "limit": limit
                    }
                },
                {
                    "$addFields": {
                        "search_score": {"$meta": "vectorSearchScore"}
                    }
                },
                {
                    "$match": {
                        "is_active": True,
                        "status": "active"
                    }
                },
                {
                    "$project": {
                        "_id": 1,
                        "title": 1,
                        "company": 1,
                        "location": 1,
                        "description": 1,
                        "skills_required": 1,
                        "job_type": 1,
                        "experience_required": 1,
                        "salary_range": 1,
                        "posted_at": 1,
                        "source": 1,
                        "job_url": 1,
                        "search_score": 1
                    }
                }
            ]
            
            results = list(db.jobs.aggregate(pipeline))
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "id": str(result["_id"]),
                    "title": result["title"],
                    "company": result["company"],
                    "location": result["location"],
                    "description": result.get("description", "")[:300] + "...",
                    "skills_required": result.get("skills_required", ""),
                    "job_type": result["job_type"],
                    "salary_range": result.get("salary_range", ""),
                    "posted_at": result["posted_at"],
                    "source": result.get("source", "unknown"),
                    "match_score": int(result["search_score"] * 100)
                })
            
            return {
                "query": query,
                "personalized": True,
                "total_results": len(formatted_results),
                "results": formatted_results
            }
        
        except Exception as e:
            logger.error(f"Error in personalized search: {str(e)}")
            # Fall back to regular search
            return await self.semantic_job_search(query, limit)
    
    def get_jobs_by_domain(
        self,
        branch: str,
        limit: int = 100,
        page: int = 1
    ) -> Dict:
        """
        Get all jobs in a specific domain/branch
        Simple filter - no embeddings needed
        
        Args:
            branch: Student's branch (e.g., "Computer Science", "Electronics")
            limit: Results per page
            page: Page number
        """
        try:
            db = self._get_db()
            
            # Branch to keywords mapping
            branch_keywords = {
                'computer': ['software', 'developer', 'programmer', 'coding', 'web', 'app', 'data', 'ai', 'ml', 'tech'],
                'electronics': ['hardware', 'embedded', 'circuit', 'electronics', 'iot', 'robotics'],
                'mechanical': ['manufacturing', 'design', 'cad', 'mechanical', 'automotive', 'production'],
                'electrical': ['electrical', 'power', 'energy', 'automation', 'control'],
                'civil': ['civil', 'construction', 'structure', 'building', 'infrastructure'],
                'chemical': ['chemical', 'process', 'plant', 'pharma', 'refinery']
            }
            
            # Find matching keywords
            keywords = []
            branch_lower = branch.lower()
            
            for key, kw_list in branch_keywords.items():
                if key in branch_lower:
                    keywords = kw_list
                    break
            
            if not keywords:
                keywords = [branch_lower]
            
            # Build regex pattern
            regex_pattern = '|'.join(keywords)
            
            # Query with pagination
            skip = (page - 1) * limit
            
            jobs = list(db.jobs.find({
                "is_active": True,
                "status": "active",
                "$or": [
                    {"title": {"$regex": regex_pattern, "$options": "i"}},
                    {"description": {"$regex": regex_pattern, "$options": "i"}},
                    {"skills_required": {"$regex": regex_pattern, "$options": "i"}}
                ]
            }).sort("posted_at", -1).skip(skip).limit(limit))
            
            # Count total
            total = db.jobs.count_documents({
                "is_active": True,
                "status": "active",
                "$or": [
                    {"title": {"$regex": regex_pattern, "$options": "i"}},
                    {"description": {"$regex": regex_pattern, "$options": "i"}},
                    {"skills_required": {"$regex": regex_pattern, "$options": "i"}}
                ]
            })
            
            # Format results
            formatted_jobs = []
            for job in jobs:
                formatted_jobs.append({
                    "id": str(job["_id"]),
                    "title": job["title"],
                    "company": job["company"],
                    "location": job["location"],
                    "description": job.get("description", "")[:300] + "...",
                    "job_type": job["job_type"],
                    "salary_range": job.get("salary_range", ""),
                    "posted_at": job["posted_at"],
                    "source": job.get("source", "unknown")
                })
            
            return {
                "branch": branch,
                "keywords_used": keywords,
                "total_jobs": total,
                "page": page,
                "limit": limit,
                "total_pages": (total + limit - 1) // limit,
                "jobs": formatted_jobs
            }
        
        except Exception as e:
            logger.error(f"Error in domain filter: {str(e)}")
            return {
                "error": str(e),
                "branch": branch,
                "total_jobs": 0,
                "jobs": []
            }
    
    async def check_vector_index_status(self) -> Dict:
        """
        Check if MongoDB Vector Search index exists and is ready
        """
        try:
            db = self._get_db()
            
            # Try a test search
            test_embedding = [0.1] * 384  # Dummy embedding
            
            result = db.jobs.aggregate([
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
            ])
            
            list(result)  # Execute the query
            
            return {
                "status": "ready",
                "index_name": self.vector_index_name,
                "message": "Vector search index is ready!"
            }
        
        except Exception as e:
            error_msg = str(e)
            
            if "index" in error_msg.lower():
                return {
                    "status": "missing",
                    "index_name": self.vector_index_name,
                    "error": "Vector search index not found",
                    "message": "Please create the index in MongoDB Atlas"
                }
            else:
                return {
                    "status": "error",
                    "error": error_msg
                }


# Singleton instance
search_service = SearchService()