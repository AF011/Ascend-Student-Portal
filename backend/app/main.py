import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager

from app.config import settings
from app.db.mongo import connect_to_mongo, close_mongo_connection
from app.api.v1 import api_router
from app.api.v1 import jobs_api, notifications_api
# Add after existing router imports
from app.api.v1 import student_jobs_api
from fastapi.responses import RedirectResponse

# ------------------ FIXED PATHS ------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
TEMPLATES_DIR = os.path.join(FRONTEND_DIR, "templates")
STATIC_DIR = os.path.join(FRONTEND_DIR, "static")
# -------------------------------------------------

# ✅ ADD JINJA2 TEMPLATES
templates = Jinja2Templates(directory=TEMPLATES_DIR)


def nocache_file_response(path: str):
    response = FileResponse(path)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@asynccontextmanager
async def lifespan(app: FastAPI):

    print("🚀 Starting up Virtual CDC Backend...")
    
    # Connect to MongoDB
    connect_to_mongo()
    
    # ✅ START THE SCHEDULER
    from app.services.job_scheduler import start_scheduler
    start_scheduler()
    
    yield
    
    print("🛑 Shutting down...")
    
    # ✅ STOP THE SCHEDULER
    from app.services.job_scheduler import stop_scheduler
    stop_scheduler()
    
    # Close MongoDB
    close_mongo_connection()


app = FastAPI(
    title=settings.APP_NAME,
    description="Ascend - Time2Progress V-1.0",
    version="1.0.0",
    lifespan=lifespan
)


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# API Routers - Import and include
app.include_router(api_router, prefix="/api/v1")

# Import new routers here to avoid circular imports at module level
from app.api.v1 import career_coach
app.include_router(career_coach.router, prefix="/api/v1")


# ------------------ HTML ROUTES ------------------

@app.get("/")
async def root():
    # ✅ index.html doesn't use Jinja2, so FileResponse is fine
    return FileResponse(os.path.join(TEMPLATES_DIR, "index.html"))


# Auth Pages (if these don't use template inheritance, keep FileResponse)
@app.get("/auth/login")
async def login_page(request: Request):
    token = request.cookies.get("access_token")

    if token:
        return RedirectResponse(url="/student/dashboard", status_code=302)

    return nocache_file_response(
        os.path.join(TEMPLATES_DIR, "auth", "login.html")
    )

@app.post("/auth/logout")
async def logout():
    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie("access_token")
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/auth/signup")
async def signup_page():
    return nocache_file_response(os.path.join(TEMPLATES_DIR, "auth", "signup.html"))


@app.get("/auth/oauth_callback")
async def oauth_callback_page():
    return FileResponse(os.path.join(TEMPLATES_DIR, "auth", "oauth_callback.html"))

# About Page
@app.get("/about")
async def about_page(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})


# Add after existing router registrations
app.include_router(student_jobs_api.router, prefix="/api/v1", tags=["student-jobs"])
# Student Pages - ✅ FIXED: Use TemplateResponse for Jinja2 templates
@app.get("/student/profile")
async def student_profile_page(request: Request):
    return templates.TemplateResponse("student/profile_form.html", {"request": request})


@app.get("/student/dashboard")
async def student_dashboard_page(request: Request):
    return templates.TemplateResponse("student/dashboard.html", {"request": request})


@app.get("/student/roadmap")
async def student_roadmap_page(request: Request):
    return templates.TemplateResponse("student/roadmap.html", {"request": request})


@app.get("/student/progress")
async def student_progress_page(request: Request):
    return templates.TemplateResponse("student/roadmap_progress.html", {"request": request})


@app.get("/student/career-coach")
async def student_coach_page(request: Request):
    return templates.TemplateResponse("student/career_coach.html", {"request": request})

# Team Page
@app.get("/innodayvoyagers")
async def innodayvoyagers_page(request: Request):
    return templates.TemplateResponse("innodayvoyagers.html", {"request": request})


# Institution Pages - ✅ FIXED: Use TemplateResponse
@app.get("/institution/profile")
async def institution_profile_page(request: Request):
    return templates.TemplateResponse("institution/profile_form.html", {"request": request})


@app.get("/institution/dashboard")
async def institution_dashboard_page(request: Request):
    return templates.TemplateResponse("institution/dashboard.html", {"request": request})

# Add to router registration section (after existing routers)
app.include_router(jobs_api.router, prefix="/api/v1", tags=["jobs"])
app.include_router(notifications_api.router, prefix="/api/v1", tags=["notifications"])



# Institution Pages - ADD THESE
@app.get("/institution/post-job")
async def institution_post_job(request: Request):
    return templates.TemplateResponse("institution/post_job.html", {"request": request})

@app.get("/institution/jobs")
async def institution_manage_jobs(request: Request):
    return templates.TemplateResponse("institution/manage_jobs.html", {"request": request})

@app.get("/institution/calendar")
async def institution_calendar(request: Request):
    return templates.TemplateResponse("institution/calendar.html", {"request": request})

# Student Job Pages - ADD THESE
# Student Job Pages
@app.get("/student/jobs")
async def student_jobs(request: Request):
    return templates.TemplateResponse("student/student_jobs.html", {"request": request})  # ← Use correct name

@app.get("/student/jobs/{job_id}")
async def student_job_detail(request: Request, job_id: str):
    return templates.TemplateResponse("student/job_detail.html", {"request": request})

@app.get("/student/my-applications")
async def student_applications(request: Request):
    return templates.TemplateResponse("student/my_applications.html", {"request": request})

@app.get("/student/bookmarks")
async def student_bookmarks(request: Request):
    return templates.TemplateResponse("student/bookmarks.html", {"request": request})

# Institution calendar
@app.get("/institution/calendar")
async def institution_calendar(request: Request):
    # Return simple coming soon page for now
    return templates.TemplateResponse("institution/dashboard.html", {"request": request})


@app.get("/debug/check-profile")
async def check_profile(request: Request):
    from app.api.dependencies import get_current_user
    try:
        user = await get_current_user(request.headers.get("Authorization", "").replace("Bearer ", ""))
        
        from app.db.mongo import get_database
        db = get_database()
        
        if user.role == "institution":
            institution = db.institutions.find_one({"user_id": user.id})
            return {
                "user_id": user.id,
                "role": user.role,
                "profile_completed": user.profile_completed,
                "has_institution_doc": institution is not None,
                "has_profile_data": institution.get("profile_data") if institution else None
            }
        else:
            student = db.students.find_one({"user_id": user.id})
            return {
                "user_id": user.id,
                "role": user.role,
                "profile_completed": user.profile_completed,
                "has_student_doc": student is not None,
                "has_profile_data": student.get("profile_data") if student else None
            }
    except Exception as e:
        return {"error": str(e)}


# ADD THESE ROUTES TO main.py

# Institution Routes
@app.get("/institution/post-job")
async def institution_post_job(request: Request):
    return templates.TemplateResponse("institution/post_job.html", {"request": request})

@app.get("/institution/jobs")
async def institution_manage_jobs(request: Request):
    return templates.TemplateResponse("institution/manage_jobs.html", {"request": request})

@app.get("/institution/applicants")
async def institution_view_applicants(request: Request):
    return templates.TemplateResponse("institution/view_applicants.html", {"request": request})

@app.get("/institution/calendar")
async def institution_calendar(request: Request):
    return templates.TemplateResponse("institution/calendar.html", {"request": request})


@app.get("/institution/analytics")
async def institution_analytics_page(request: Request):
    """Analytics dashboard for institutions"""
    return templates.TemplateResponse("institution/analytics_dashboard.html", {"request": request})


@app.get("/student/analytics")
async def student_analytics_page():
    """Analytics dashboard for students"""
    return FileResponse(os.path.join(TEMPLATES_DIR, "student", "analytics_dashboard.html"))

# Optional: Admin analytics
@app.get("/admin/analytics")
async def admin_analytics_page(request: Request):
    """Analytics dashboard for admins"""
    return templates.TemplateResponse("admin/analytics_dashboard.html", {"request": request})

# Health Check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "database": "connected"}