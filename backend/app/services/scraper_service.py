"""
Path: backend/app/services/scraper_service.py

Job Scraper Service - Uses JobSpy to scrape from Indeed, LinkedIn, ZipRecruiter
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from jobspy import scrape_jobs
from app.db.mongo import get_database
from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)


class JobScraperService:
    """Service for scraping and storing job postings"""
    
    def __init__(self):
        self.db = None
    
    def _get_db(self):
        """Get database connection"""
        if self.db is None:
            self.db = get_database()
        return self.db
    
    async def scrape_jobs(
        self,
        search_term: str,
        location: str = "India",
        results_wanted: int = 20,
        hours_old: int = 72,
        country_indeed: str = "India"
    ) -> Dict:
        """
        Scrape jobs using JobSpy from Indeed, LinkedIn, and ZipRecruiter
        
        Args:
            search_term: Job search query (e.g., "software engineer")
            location: Location for job search
            results_wanted: Number of results to fetch
            hours_old: Only get jobs posted within this many hours
            country_indeed: Country for Indeed scraping
            
        Returns:
            Dictionary with scraping statistics
        """
        try:
            logger.info(f"🔍 Scraping jobs for: '{search_term}' in {location}")
            
            # Use JobSpy to scrape from multiple sources
            jobs_df = scrape_jobs(
                site_name=["indeed", "linkedin", "zip_recruiter"],
                search_term=search_term,
                location=location,
                results_wanted=results_wanted,
                hours_old=hours_old,
                country_indeed=country_indeed,
                linkedin_fetch_description=True,
                linkedin_company_ids=None
            )
            
            if jobs_df is None or jobs_df.empty:
                logger.warning(f"No jobs found for '{search_term}'")
                return {
                    "search_term": search_term,
                    "total_scraped": 0,
                    "saved": 0,
                    "duplicates": 0,
                    "failed": 0
                }
            
            total_scraped = len(jobs_df)
            logger.info(f"✅ Scraped {total_scraped} jobs for '{search_term}'")
            
            # Convert to list of dicts
            jobs_list = jobs_df.to_dict('records')
            
            return {
                "search_term": search_term,
                "total_scraped": total_scraped,
                "jobs": jobs_list
            }
            
        except Exception as e:
            logger.error(f"❌ Error scraping jobs for '{search_term}': {str(e)}")
            return {
                "search_term": search_term,
                "total_scraped": 0,
                "error": str(e)
            }
    
    async def store_job(self, job_data: Dict) -> Optional[str]:
        """
        Store a single job in the database with embedding
        
        Args:
            job_data: Job data from scraper
            
        Returns:
            Job ID if successful, None if duplicate or error
        """
        try:
            db = self._get_db()
            
            # Extract and normalize job data
            job_doc = self._normalize_job_data(job_data)
            
            # Check for duplicates
            existing = db.jobs.find_one({
                "title": job_doc["title"],
                "company": job_doc["company"],
                "location": job_doc["location"]
            })
            
            if existing:
                logger.debug(f"Duplicate job: {job_doc['title']} at {job_doc['company']}")
                return None
            
            # Generate embedding for the job
            try:
                embedding = await embedding_service.generate_job_embedding(job_doc)
                job_doc["job_embedding"] = embedding
                job_doc["embedding_generated_at"] = datetime.utcnow()
                job_doc["embedding_model"] = embedding_service.model_name
            except Exception as e:
                logger.warning(f"Failed to generate embedding for job: {str(e)}")
                # Continue without embedding
                job_doc["job_embedding"] = None
            
            # Insert into database
            result = db.jobs.insert_one(job_doc)
            
            logger.debug(f"✅ Saved job: {job_doc['title']} at {job_doc['company']}")
            
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"❌ Error storing job: {str(e)}")
            return None
    
    def _normalize_job_data(self, raw_job: Dict) -> Dict:
        """
        Normalize job data from scraper to database format
        
        Args:
            raw_job: Raw job data from JobSpy
            
        Returns:
            Normalized job document
        """
        # Map JobSpy fields to our database schema
        now = datetime.utcnow()
        
        job_doc = {
            # Basic info
            "title": raw_job.get("title", "Unknown Title"),
            "company": raw_job.get("company", "Unknown Company"),
            "location": raw_job.get("location", "Unknown Location"),
            
            # Description
            "description": raw_job.get("description", ""),
            
            # Job details
            "job_type": self._normalize_job_type(raw_job.get("job_type")),
            "salary_range": self._extract_salary(raw_job),
            "experience_required": raw_job.get("job_level", "Not specified"),
            
            # Skills (extract from description if available)
            "skills_required": self._extract_skills(raw_job),
            
            # Links
            "job_url": raw_job.get("job_url", ""),
            "source": raw_job.get("site", "unknown"),
            
            # Metadata
            "posted_at": self._parse_date_posted(raw_job.get("date_posted")),
            "scraped_at": now,
            "is_active": True,
            "status": "active",
            
            # Counters
            "views_count": 0,
            "applications_count": 0,
            
            # Raw data for reference
            "raw_data": raw_job
        }
        
        return job_doc
    
    def _normalize_job_type(self, job_type: Optional[str]) -> str:
        """Normalize job type to our standard values"""
        if not job_type:
            return "full_time"
        
        job_type_lower = job_type.lower()
        
        if "intern" in job_type_lower:
            return "internship"
        elif "part" in job_type_lower or "part-time" in job_type_lower:
            return "part_time"
        elif "contract" in job_type_lower or "freelance" in job_type_lower:
            return "contract"
        else:
            return "full_time"
    
    def _extract_salary(self, raw_job: Dict) -> str:
        """Extract and format salary information"""
        min_salary = raw_job.get("min_amount")
        max_salary = raw_job.get("max_amount")
        interval = raw_job.get("interval", "")
        currency = raw_job.get("currency", "INR")
        
        if min_salary and max_salary:
            return f"{currency} {min_salary:,.0f} - {max_salary:,.0f} {interval}"
        elif min_salary:
            return f"{currency} {min_salary:,.0f}+ {interval}"
        elif max_salary:
            return f"Up to {currency} {max_salary:,.0f} {interval}"
        else:
            return "Not specified"
    
    def _extract_skills(self, raw_job: Dict) -> str:
        """Extract skills from job description"""
        description = raw_job.get("description", "").lower()
        
        # Common tech skills
        common_skills = [
            "python", "java", "javascript", "react", "node.js", "angular", "vue",
            "sql", "mongodb", "postgresql", "aws", "azure", "gcp", "docker", "kubernetes",
            "machine learning", "deep learning", "tensorflow", "pytorch", "scikit-learn",
            "html", "css", "typescript", "c++", "c#", "go", "rust", "ruby",
            "django", "flask", "fastapi", "spring boot", "express.js",
            "git", "jenkins", "ci/cd", "agile", "scrum", "jira"
        ]
        
        found_skills = [skill for skill in common_skills if skill in description]
        
        return ", ".join(found_skills) if found_skills else "See description"
    
    def _parse_date_posted(self, date_str: Optional[str]) -> datetime:
        """Parse date posted from various formats"""
        if not date_str:
            return datetime.utcnow()
        
        try:
            # Try parsing ISO format
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            # Default to current time if parsing fails
            return datetime.utcnow()
    
    async def scrape_and_store_jobs(
        self,
        search_terms: List[str],
        location: str = "India",
        results_per_term: int = 15
    ) -> Dict:
        """
        Scrape jobs for multiple search terms and store them
        
        Args:
            search_terms: List of job search queries
            location: Location for job search
            results_per_term: Results wanted per search term
            
        Returns:
            Statistics about the scraping operation
        """
        stats = {
            "total_scraped": 0,
            "total_saved": 0,
            "total_duplicates": 0,
            "total_failed": 0,
            "by_term": {}
        }
        
        for search_term in search_terms:
            logger.info(f"\n{'='*60}")
            logger.info(f"🔍 Processing: {search_term}")
            logger.info(f"{'='*60}")
            
            # Scrape jobs for this search term
            scrape_result = await self.scrape_jobs(
                search_term=search_term,
                location=location,
                results_wanted=results_per_term,
                hours_old=72
            )
            
            if "error" in scrape_result:
                stats["by_term"][search_term] = {
                    "scraped": 0,
                    "saved": 0,
                    "duplicates": 0,
                    "error": scrape_result["error"]
                }
                continue
            
            jobs = scrape_result.get("jobs", [])
            scraped_count = len(jobs)
            saved_count = 0
            duplicate_count = 0
            
            # Store each job
            for job in jobs:
                job_id = await self.store_job(job)
                if job_id:
                    saved_count += 1
                else:
                    duplicate_count += 1
            
            # Update stats
            stats["total_scraped"] += scraped_count
            stats["total_saved"] += saved_count
            stats["total_duplicates"] += duplicate_count
            
            stats["by_term"][search_term] = {
                "scraped": scraped_count,
                "saved": saved_count,
                "duplicates": duplicate_count
            }
            
            logger.info(f"✅ {search_term}: Scraped {scraped_count}, Saved {saved_count}, Duplicates {duplicate_count}")
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 TOTAL SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Total Scraped: {stats['total_scraped']}")
        logger.info(f"✅ Total Saved: {stats['total_saved']}")
        logger.info(f"🔄 Total Duplicates: {stats['total_duplicates']}")
        logger.info(f"{'='*60}\n")
        
        return stats
    
    async def cleanup_old_unbookmarked_jobs(self, days_old: int = 7) -> int:
        """
        Remove old jobs that haven't been bookmarked
        
        Args:
            days_old: Delete jobs older than this many days
            
        Returns:
            Number of jobs deleted
        """
        try:
            db = self._get_db()
            
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            # Find old jobs that are not bookmarked
            result = db.jobs.delete_many({
                "posted_at": {"$lt": cutoff_date},
                "is_bookmarked": {"$ne": True}
            })
            
            deleted_count = result.deleted_count
            
            logger.info(f"🗑️ Deleted {deleted_count} jobs older than {days_old} days")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ Error cleaning up old jobs: {str(e)}")
            return 0
    
    async def get_scraping_stats(self) -> Dict:
        """Get statistics about scraped jobs"""
        try:
            db = self._get_db()
            
            total_jobs = db.jobs.count_documents({})
            active_jobs = db.jobs.count_documents({"is_active": True})
            
            # Jobs by source
            pipeline = [
                {"$group": {"_id": "$source", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]
            by_source = list(db.jobs.aggregate(pipeline))
            
            # Jobs by type
            pipeline = [
                {"$group": {"_id": "$job_type", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]
            by_type = list(db.jobs.aggregate(pipeline))
            
            # Recent jobs (last 24 hours)
            yesterday = datetime.utcnow() - timedelta(hours=24)
            recent_jobs = db.jobs.count_documents({
                "scraped_at": {"$gte": yesterday}
            })
            
            return {
                "total_jobs": total_jobs,
                "active_jobs": active_jobs,
                "recent_jobs_24h": recent_jobs,
                "by_source": by_source,
                "by_type": by_type
            }
            
        except Exception as e:
            logger.error(f"Error getting scraping stats: {str(e)}")
            return {}


# Singleton instance
job_scraper_service = JobScraperService()