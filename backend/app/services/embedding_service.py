"""
Path: backend/app/services/embedding_service.py

MERGED VERSION - Best of both worlds:
1. Lazy loading (no startup hang)
2. Focused embeddings (high match scores 77-78%)
3. Batch processing (from friend's version)
4. Job embeddings (needed for recommendations)

Author: Virtual CDC Team
Date: December 2024
"""

import asyncio
import logging
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating FOCUSED embeddings - only relevant matching data
    
    Uses sentence-transformers to convert profiles/jobs into 384-dim vectors
    for semantic similarity matching.
    """
    
    def __init__(self):
        # ✅ LAZY LOADING - Don't load model on init (prevents startup hang)
        self.model = None
        self.model_name = 'all-MiniLM-L6-v2'
        self.embedding_dim = 384
    
    def _load_model(self):
        """
        Lazy load the model only when first needed
        This prevents server startup from hanging while model downloads/loads
        """
        if self.model is None:
            logger.info(f"⏳ Loading embedding model: {self.model_name}...")
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(self.model_name)
                self.embedding_dim = self.model.get_sentence_embedding_dimension()
                logger.info(f"✅ Model loaded successfully! Dimension: {self.embedding_dim}")
            except Exception as e:
                logger.error(f"❌ Failed to load model: {str(e)}")
                raise
        return self.model
    
    def _prepare_profile_text(self, profile_data: Dict) -> str:
        """
        Convert profile to text - ONLY RELEVANT FIELDS FOR MATCHING
        
        ✅ INCLUDE: Branch, Skills, Projects, Experience, Interests
        ❌ EXCLUDE: Name, Location, College, CGPA, Dates, Gender
        
        Why? Embeddings should capture MATCHING CRITERIA, not metadata!
        """
        text_parts = []
        
        # ==================== RELEVANT FIELDS ONLY ====================
        
        # 1. Branch/Domain (VERY IMPORTANT)
        if profile_data.get('branch'):
            branch = profile_data['branch']
            text_parts.append(f"Branch: {branch}")
            text_parts.append(f"Domain: {branch}")  # Reinforce domain
        
        # 2. Degree (if relevant)
        if profile_data.get('degree'):
            text_parts.append(f"Degree: {profile_data['degree']}")
        
        # 3. Technical Skills (MOST IMPORTANT!)
        if profile_data.get('technical_skills'):
            skills = profile_data['technical_skills']
            text_parts.append(f"Skills: {skills}")
            text_parts.append(f"Technical expertise: {skills}")  # Reinforce
        
        # 4. Soft Skills
        if profile_data.get('soft_skills'):
            text_parts.append(f"Soft skills: {profile_data['soft_skills']}")
        
        # 5. Languages (keep this - can be relevant)
        if profile_data.get('languages'):
            text_parts.append(f"Languages: {profile_data['languages']}")
        
        # 6. Experience (IMPORTANT)
        if profile_data.get('experience'):
            exp = profile_data['experience']
            if len(exp) > 10:  # Only if meaningful
                text_parts.append(f"Experience: {exp}")
        
        # 7. Projects (IMPORTANT)
        if profile_data.get('projects'):
            projects = profile_data['projects']
            if len(projects) > 10:  # Only if meaningful
                text_parts.append(f"Projects: {projects}")
        
        # 8. Certifications
        if profile_data.get('certifications'):
            certs = profile_data['certifications']
            if len(certs) > 5:  # Only if meaningful
                text_parts.append(f"Certifications: {certs}")
        
        # 9. Preferred Roles (IMPORTANT)
        if profile_data.get('preferred_roles'):
            text_parts.append(f"Seeking roles: {profile_data['preferred_roles']}")
        
        # 10. Preferred Industries (can be relevant)
        if profile_data.get('preferred_industries'):
            industries = profile_data['preferred_industries']
            if len(industries) > 3:
                text_parts.append(f"Industries: {industries}")
        
        profile_text = " | ".join(filter(None, text_parts))
        
        logger.debug(f"Profile text (focused): {len(profile_text)} chars")
        
        return profile_text
    
    def _prepare_job_text(self, job_data: Dict) -> str:
        """
        Convert job to text - ONLY RELEVANT FIELDS FOR MATCHING
        
        ✅ INCLUDE: Title, Description, Requirements, Skills
        ❌ EXCLUDE: Company name, Location, Salary, Posted date
        
        Why? Focus on JOB REQUIREMENTS, not metadata!
        """
        text_parts = []
        
        # ==================== RELEVANT FIELDS ONLY ====================
        
        # 1. Job Title (VERY IMPORTANT)
        if job_data.get('title'):
            title = job_data['title']
            text_parts.append(f"Job title: {title}")
            text_parts.append(f"Role: {title}")  # Reinforce
        
        # 2. Job Description (MOST IMPORTANT)
        if job_data.get('description'):
            desc = job_data['description']
            # Take first 500 chars (full description might be too long)
            desc = desc[:500] if len(desc) > 500 else desc
            text_parts.append(f"Description: {desc}")
        
        # 3. Requirements (IMPORTANT)
        if job_data.get('requirements'):
            req = job_data['requirements']
            req = req[:300] if len(req) > 300 else req
            text_parts.append(f"Requirements: {req}")
        
        # 4. Skills Required (VERY IMPORTANT)
        if job_data.get('skills_required'):
            skills = job_data['skills_required']
            text_parts.append(f"Skills needed: {skills}")
            text_parts.append(f"Technologies: {skills}")  # Reinforce
        
        # 5. Job Type (helpful context)
        if job_data.get('job_type'):
            text_parts.append(f"Type: {job_data['job_type']}")
        
        # 6. Experience Required
        if job_data.get('experience_required'):
            text_parts.append(f"Experience: {job_data['experience_required']}")
        
        job_text = " | ".join(filter(None, text_parts))
        
        logger.debug(f"Job text (focused): {len(job_text)} chars")
        
        return job_text
    
    async def generate_profile_embedding(self, profile_data: Dict) -> List[float]:
        """
        Generate focused embedding for student profile
        
        Args:
            profile_data: Dictionary containing profile information
            
        Returns:
            List of 384 floats (embedding vector)
            
        Raises:
            ValueError: If profile_data is empty or invalid
        """
        if not profile_data:
            raise ValueError("Profile data cannot be empty")
        
        try:
            # Lazy load model
            model = self._load_model()
            
            profile_text = self._prepare_profile_text(profile_data)
            
            if not profile_text or len(profile_text.strip()) == 0:
                logger.warning("Empty profile text - using default")
                profile_text = "No profile information"
            
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None,
                lambda: model.encode(profile_text, convert_to_numpy=True)
            )
            
            embedding_list = embedding.tolist()
            
            logger.info(f"✅ Generated focused profile embedding: {len(embedding_list)} dims")
            
            return embedding_list
        
        except Exception as e:
            logger.error(f"Error generating profile embedding: {str(e)}")
            raise Exception(f"Profile embedding generation failed: {str(e)}")
    
    async def generate_job_embedding(self, job_data: Dict = None, title: str = None, description: str = None, skills: str = None, requirements: str = None) -> List[float]:
        """
        Generate focused embedding for job posting
        
        Args:
            job_data: Dictionary containing job information (if using dict)
            title: Job title (if using individual params)
            description: Job description (if using individual params)
            skills: Required skills (if using individual params)
            requirements: Job requirements (if using individual params)
            
        Returns:
            List of 384 floats (embedding vector)
        """
        # ✅ ADDED: Support both dict and individual parameters
        if job_data is None:
            # Build job_data from individual params
            job_data = {}
            if title:
                job_data['title'] = title
            if description:
                job_data['description'] = description
            if skills:
                job_data['skills_required'] = skills
            if requirements:
                job_data['requirements'] = requirements
        
        if not job_data:
            raise ValueError("Job data cannot be empty")
        
        try:
            # Lazy load model
            model = self._load_model()
            
            job_text = self._prepare_job_text(job_data)
            
            if not job_text or len(job_text.strip()) == 0:
                logger.warning("Empty job text - using default")
                job_text = "No job information"
            
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None,
                lambda: model.encode(job_text, convert_to_numpy=True)
            )
            
            embedding_list = embedding.tolist()
            
            logger.info(f"✅ Generated focused job embedding: {len(embedding_list)} dims")
            
            return embedding_list
        
        except Exception as e:
            logger.error(f"Error generating job embedding: {str(e)}")
            raise Exception(f"Job embedding generation failed: {str(e)}")
    
    async def generate_text_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for search query text
        
        Args:
            text: Any text string (e.g., search query)
            
        Returns:
            List of 384 floats (embedding vector)
        """
        try:
            # Lazy load model
            model = self._load_model()
            
            if not text or not text.strip():
                logger.warning("Empty text - using default")
                text = "search query"
            
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None,
                lambda: model.encode(text, convert_to_numpy=True)
            )
            
            embedding_list = embedding.tolist()
            
            logger.debug(f"Generated text embedding: {len(embedding_list)} dims")
            
            return embedding_list
        
        except Exception as e:
            logger.error(f"Error generating text embedding: {str(e)}")
            raise
    
    async def batch_generate_embeddings(self, profiles: List[Dict]) -> List[List[float]]:
        """
        Generate embeddings for multiple profiles at once (more efficient)
        
        Args:
            profiles: List of profile data dictionaries
            
        Returns:
            List of embedding vectors
        """
        if not profiles:
            return []
        
        try:
            # Lazy load model
            model = self._load_model()
            
            # Prepare all profile texts
            profile_texts = [self._prepare_profile_text(profile) for profile in profiles]
            
            # Filter out empty texts
            valid_texts = [text for text in profile_texts if text and len(text.strip()) > 0]
            
            if not valid_texts:
                raise ValueError("No valid profile texts to encode")
            
            # Generate embeddings in batch (more efficient)
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                lambda: model.encode(valid_texts, convert_to_numpy=True)
            )
            
            # Convert to list of lists
            embeddings_list = [emb.tolist() for emb in embeddings]
            
            logger.info(f"Successfully generated {len(embeddings_list)} embeddings in batch")
            
            return embeddings_list
        
        except Exception as e:
            logger.error(f"Batch embedding generation failed: {str(e)}")
            raise Exception(f"Batch embedding generation failed: {str(e)}")
    
    def get_model_info(self) -> Dict:
        """
        Get information about the current embedding model
        
        Returns:
            Dictionary with model information
        """
        if self.model is None:
            return {
                "model_name": self.model_name,
                "embedding_dimension": self.embedding_dim,
                "status": "not_loaded"
            }
        
        return {
            "model_name": self.model_name,
            "embedding_dimension": self.embedding_dim,
            "max_seq_length": self.model.max_seq_length,
            "status": "loaded"
        }


# Singleton instance
embedding_service = EmbeddingService()