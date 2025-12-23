"""
Path: backend/app/services/job_scheduler.py

SMART Job Scheduler - Dynamically scrapes based on student profiles
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import logging
import pytz
from typing import List, Set
from app.services.scraper_service import job_scraper_service
from app.db.mongo import get_database

logger = logging.getLogger(__name__)

# Create scheduler instance with IST timezone
IST = pytz.timezone('Asia/Kolkata')
scheduler = AsyncIOScheduler(timezone=IST)


def extract_dynamic_search_terms() -> List[str]:
    """
    Extract search terms dynamically from student profiles
    
    Returns:
        List of unique search terms based on student skills, interests, and roles
    """
    try:
        db = get_database()
        
        logger.info("=" * 70)
        logger.info("🔍 EXTRACTING DYNAMIC SEARCH TERMS FROM STUDENT PROFILES")
        logger.info("=" * 70)
        
        # Get all students with completed profiles
        students = list(db.users.find({
            "role": "student",
            "profile_completed": True,
            "profile_data": {"$exists": True}
        }))
        
        logger.info(f"📊 Found {len(students)} students with completed profiles")
        
        if not students:
            logger.warning("⚠️ No students found, using default terms")
            return get_default_search_terms()
        
        # Collect all skills, interests, and preferred roles
        all_skills: Set[str] = set()
        all_interests: Set[str] = set()
        all_roles: Set[str] = set()
        all_branches: Set[str] = set()
        
        for student in students:
            profile_data = student.get("profile_data", {})
            
            # Extract technical skills
            tech_skills = profile_data.get("technical_skills", "")
            if tech_skills:
                skills_list = [s.strip().lower() for s in tech_skills.split(",")]
                all_skills.update(skills_list)
            
            # Extract soft skills
            soft_skills = profile_data.get("soft_skills", "")
            if soft_skills:
                skills_list = [s.strip().lower() for s in soft_skills.split(",")]
                all_skills.update(skills_list)
            
            # Extract interests
            interests = profile_data.get("interests", "")
            if interests:
                interests_list = [i.strip().lower() for i in interests.split(",")]
                all_interests.update(interests_list)
            
            # Extract preferred roles
            preferred_roles = profile_data.get("preferred_roles", "")
            if preferred_roles:
                roles_list = [r.strip().lower() for r in preferred_roles.split(",")]
                all_roles.update(roles_list)
            
            # Extract branch
            branch = profile_data.get("branch", "")
            if branch:
                all_branches.add(branch.strip().lower())
        
        logger.info(f"📌 Extracted {len(all_skills)} unique skills")
        logger.info(f"📌 Extracted {len(all_interests)} unique interests")
        logger.info(f"📌 Extracted {len(all_roles)} unique roles")
        logger.info(f"📌 Extracted {len(all_branches)} unique branches")
        
        # Build search terms
        search_terms: Set[str] = set()
        
        # Add preferred roles (highest priority)
        for role in all_roles:
            if len(role) > 3:  # Skip very short terms
                search_terms.add(role)
                # Add with "fresher" for entry-level
                if "engineer" in role or "developer" in role or "analyst" in role:
                    search_terms.add(f"{role} fresher")
                    search_terms.add(f"{role} intern")
        
        # Add skills as search terms
        skill_keywords = [
            "python", "java", "javascript", "react", "angular", "node.js", "nodejs",
            "machine learning", "data science", "web development", "frontend", "backend",
            "full stack", "devops", "cloud", "aws", "azure", "android", "ios",
            "flutter", "react native", "ui/ux", "graphic design", "digital marketing",
            "content writing", "seo", "data analyst", "business analyst",
            "mechanical", "cad", "autocad", "solidworks", "civil", "electrical",
            "embedded", "iot", "robotics", "automation"
        ]
        
        for skill in all_skills:
            skill_clean = skill.strip().lower()
            if skill_clean in skill_keywords and len(skill_clean) > 3:
                search_terms.add(f"{skill_clean} developer")
                search_terms.add(f"{skill_clean} intern")
        
        # Add branch-based terms
        branch_mapping = {
            "computer science": ["software engineer", "web developer", "data analyst"],
            "information technology": ["software engineer", "web developer", "it support"],
            "mechanical": ["mechanical engineer", "cad designer", "manufacturing engineer"],
            "electrical": ["electrical engineer", "embedded engineer", "electronics"],
            "civil": ["civil engineer", "structural engineer", "site engineer"],
            "electronics": ["electronics engineer", "embedded developer", "iot engineer"]
        }
        
        for branch in all_branches:
            branch_lower = branch.lower()
            for key, terms in branch_mapping.items():
                if key in branch_lower:
                    for term in terms:
                        search_terms.add(term)
                        search_terms.add(f"{term} fresher")
        
        # Add interest-based terms
        for interest in all_interests:
            interest_clean = interest.strip().lower()
            if len(interest_clean) > 5:  # Skip very short interests
                if any(keyword in interest_clean for keyword in ["development", "design", "engineering", "analysis"]):
                    search_terms.add(interest_clean)
        
        # Convert to list and limit to top 30 terms
        final_terms = list(search_terms)[:30]
        
        logger.info(f"✅ Generated {len(final_terms)} dynamic search terms")
        logger.info(f"Sample terms: {', '.join(final_terms[:5])}")
        
        return final_terms if final_terms else get_default_search_terms()
        
    except Exception as e:
        logger.error(f"❌ Error extracting search terms: {str(e)}")
        return get_default_search_terms()


def get_default_search_terms() -> List[str]:
    """Fallback search terms if no student data available"""
    return [
        "software engineer fresher",
        "web developer intern",
        "data analyst fresher",
        "python developer",
        "java developer fresher",
        "frontend developer react",
        "backend developer",
        "full stack developer fresher",
        "mechanical engineer fresher",
        "electrical engineer fresher"
    ]


async def scheduled_job_scraping():
    """
    Smart scheduled job scraping using dynamic search terms from student profiles
    """
    try:
        logger.info("=" * 70)
        logger.info("🤖 SMART SCHEDULED JOB SCRAPING STARTED")
        logger.info(f"⏰ Time: {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST')}")
        logger.info("=" * 70)
        
        # Get dynamic search terms from student profiles
        search_terms = extract_dynamic_search_terms()
        
        logger.info(f"🎯 Scraping jobs for {len(search_terms)} terms based on student profiles")
        
        # Scrape and store jobs
        stats = await job_scraper_service.scrape_and_store_jobs(
            search_terms=search_terms,
            location="India",
            results_per_term=15
        )
        
        logger.info("=" * 70)
        logger.info("📊 SMART SCRAPING SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Search Terms Used: {len(search_terms)}")
        logger.info(f"Total Scraped: {stats['total_scraped']}")
        logger.info(f"✅ Successfully Saved: {stats['total_saved']}")
        logger.info(f"🔄 Duplicates Skipped: {stats['total_duplicates']}")
        logger.info(f"❌ Failed: {stats['total_failed']}")
        logger.info("=" * 70)
        
        # Cleanup old jobs
        logger.info("🧹 Running cleanup...")
        
        deleted = await job_scraper_service.cleanup_old_unbookmarked_jobs(days_old=7)
        
        logger.info(f"🗑️ Deleted {deleted} old unbookmarked jobs")
        logger.info("✅ Smart scheduled job scraping completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Scheduled job scraping failed: {str(e)}")


def start_scheduler():
    """
    Start the smart job scheduler
    Runs at 6:11 AM and 7:11 PM IST daily (dynamically based on student profiles)
    """
    try:
        # Schedule for 6:11 AM IST
        scheduler.add_job(
            scheduled_job_scraping,
            trigger=CronTrigger(hour=6, minute=11),
            id='morning_scrape',
            name='Smart Morning Scrape (6:11 AM IST)',
            replace_existing=True
        )
        
        # Schedule for 7:11 PM IST (19:11)
        scheduler.add_job(
            scheduled_job_scraping,
            trigger=CronTrigger(hour=22, minute=30),
            id='evening_scrape',
            name='Smart Evening Scrape (6:11 PM IST)',
            replace_existing=True
        )
        
        # Start the scheduler
        scheduler.start()
        
        logger.info("=" * 70)
        logger.info("✅ SMART JOB SCHEDULER STARTED SUCCESSFULLY")
        logger.info("🧠 Dynamic scraping based on student profiles")
        logger.info("⏰ Morning Scrape: 6:11 AM IST (Daily)")
        logger.info("⏰ Evening Scrape: 7:11 PM IST (Daily)")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"❌ Failed to start scheduler: {str(e)}")


def stop_scheduler():
    """Stop the job scheduler"""
    try:
        scheduler.shutdown()
        logger.info("🛑 Smart job scheduler stopped")
    except Exception as e:
        logger.error(f"❌ Failed to stop scheduler: {str(e)}")


def get_scheduled_jobs():
    """Get list of scheduled jobs"""
    jobs = scheduler.get_jobs()
    return [
        {
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.strftime('%Y-%m-%d %H:%M:%S IST') if job.next_run_time else None
        }
        for job in jobs
    ]


async def trigger_manual_scrape():
    """
    Manually trigger smart job scraping (for testing)
    """
    logger.info("🔧 MANUAL SMART SCRAPING TRIGGERED")
    await scheduled_job_scraping()