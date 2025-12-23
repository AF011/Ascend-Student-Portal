"""
Path: backend/app/api/v1/scheduler.py

Scheduler API - Manual trigger and status check
"""

from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from app.services.job_scheduler import (
    trigger_manual_scrape,
    get_scheduled_jobs
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scheduler", tags=["Scheduler"])


@router.get("/status")
async def get_scheduler_status():
    """
    Get scheduler status and upcoming jobs
    """
    try:
        jobs = get_scheduled_jobs()
        
        return {
            "status": "running",
            "scheduled_jobs": jobs,
            "message": "Scheduler is active"
        }
    
    except Exception as e:
        logger.error(f"Error getting scheduler status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {str(e)}"
        )


@router.post("/trigger-scrape")
async def manual_trigger_scrape(background_tasks: BackgroundTasks):
    """
    Manually trigger job scraping immediately
    (Useful for testing or immediate updates)
    """
    try:
        # Run in background so API responds immediately
        background_tasks.add_task(trigger_manual_scrape)
        
        return {
            "message": "Job scraping triggered successfully",
            "status": "running in background"
        }
    
    except Exception as e:
        logger.error(f"Error triggering scrape: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {str(e)}"
        )