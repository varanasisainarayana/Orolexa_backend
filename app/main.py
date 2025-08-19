import os
from fastapi import FastAPI, HTTPException, Depends, File, UploadFile
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from datetime import datetime
import shutil
import mimetypes
import google.generativeai as genai
from sqlmodel import Session, select
import logging

from . import auth
from .database import create_db_and_tables, get_session
from .utils import decode_jwt_token
from .models import AnalysisHistory, User
from .config import settings
from .middleware import (
    RateLimitMiddleware, 
    SecurityMiddleware, 
    LoggingMiddleware, 
    ErrorHandlingMiddleware
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format=settings.LOG_FORMAT
)
logger = logging.getLogger(__name__)

# Configure Gemini API
genai.configure(api_key=settings.GEMINI_API_KEY)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Dental AI API...")
    create_db_and_tables()
    logger.info("Database initialized successfully")
    yield
    # Shutdown
    logger.info("Shutting down Dental AI API...")

# Initialize FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan
)

# Add middleware
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(SecurityMiddleware)
app.add_middleware(RateLimitMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.ALLOWED_METHODS,
    allow_headers=settings.ALLOWED_HEADERS,
)

# Mount static files for uploaded images
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Auth scheme
oauth2_scheme = HTTPBearer()

# Include authentication router
app.include_router(auth.router)

# Include analysis router
from . import analysis
app.include_router(analysis.router)

# Health check endpoint
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.utcnow().isoformat(),
        "environment": "railway" if settings.RAILWAY_ENVIRONMENT else "local",
        "port": settings.PORT
    }

# Dependency to get current user from JWT
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    token = credentials.credentials
    payload = decode_jwt_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return int(payload.get("sub"))  # user_id as int

# ------------------------
# Upload Images (three inputs, only first required)
# ------------------------
@app.post("/upload-image")
def upload_image(
    file1: UploadFile = File(...),
    file2: UploadFile = File(None),
    file3: UploadFile = File(None),
    current_user: int = Depends(get_current_user)
):
    try:
        upload_dir = settings.UPLOAD_DIR
        os.makedirs(upload_dir, exist_ok=True)

        saved_paths = []
        for f in [file1, file2, file3]:
            if not f:
                continue
                
            # Validate file type
            if f.content_type not in settings.ALLOWED_IMAGE_TYPES:
                raise HTTPException(status_code=415, detail=f"File type {f.content_type} not allowed")
                
            # Validate file size
            f.file.seek(0, 2)
            file_size = f.file.tell()
            f.file.seek(0)
            
            if file_size > settings.MAX_FILE_SIZE:
                raise HTTPException(status_code=413, detail=f"File too large (max {settings.MAX_FILE_SIZE // (1024*1024)}MB)")
            
            path = os.path.join(upload_dir, f"{datetime.utcnow().timestamp()}_{f.filename}")
            with open(path, "wb") as buffer:
                shutil.copyfileobj(f.file, buffer)
            saved_paths.append(path)

        return {
            "success": True,
            "data": {
                "message": "Images uploaded successfully",
                "file_paths": saved_paths,
                "uploaded_by": current_user,
                "total_images": len(saved_paths)
            }
        }
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

# Analysis endpoints are now handled by the dedicated analysis router

# ------------------------
# Redirect old analyze endpoint to new location
# ------------------------
@app.post("/analyze-image")
def redirect_analyze_image(
    file1: UploadFile = File(...),
    file2: UploadFile = File(None),
    file3: UploadFile = File(None),
    current_user: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Redirect /analyze-image to /analysis/analyze-images for backward compatibility"""
    from .analysis import analyze_images
    return analyze_images(file1, file2, file3, current_user, session)

# History endpoints are now handled by the dedicated analysis router

# ------------------------
# Redirect old history endpoint to new location
# ------------------------
@app.get("/history")
def redirect_history(
    current_user: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Redirect /history to /analysis/history for backward compatibility"""
    from .analysis import get_history
    return get_history(current_user, session)

# ------------------------
# Get User Profile
# ------------------------
@app.get("/profile")
def get_profile(
    current_user: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    user = session.exec(select(User).where(User.id == current_user)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": user.id,
        "full_name": user.full_name,
        "mobile_number": user.mobile_number,
        "profile_photo_url": user.profile_photo_url,
        "created_at": user.created_at.isoformat()
    }

# ------------------------
# Update User Profile
# ------------------------
@app.put("/profile")
def update_profile(
    full_name: str = None,
    profile_photo: UploadFile = File(None),
    current_user: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    user = session.exec(select(User).where(User.id == current_user)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update full name if provided
    if full_name:
        user.full_name = full_name
    
    # Update profile photo if provided
    if profile_photo:
        # Validate file type
        if profile_photo.content_type not in settings.ALLOWED_IMAGE_TYPES:
            raise HTTPException(status_code=415, detail="Invalid file type")
            
        # Validate file size
        profile_photo.file.seek(0, 2)
        file_size = profile_photo.file.tell()
        profile_photo.file.seek(0)
        
        if file_size > settings.MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="File too large")
        
        uploads_dir = f"{settings.UPLOAD_DIR}/profiles"
        os.makedirs(uploads_dir, exist_ok=True)
        ext = os.path.splitext(profile_photo.filename)[1]
        filename = f"{datetime.utcnow().timestamp()}_{profile_photo.filename}"
        saved_path = os.path.join(uploads_dir, filename)
        
        try:
            with open(saved_path, "wb") as f:
                shutil.copyfileobj(profile_photo.file, f)
            user.profile_photo_url = saved_path
        except Exception as e:
            logger.error(f"Profile photo save error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Could not save profile photo: {e}")
    
    session.add(user)
    session.commit()
    session.refresh(user)
    
    return {
        "id": user.id,
        "full_name": user.full_name,
        "mobile_number": user.mobile_number,
        "profile_photo_url": user.profile_photo_url,
        "created_at": user.created_at.isoformat()
    }

# ------------------------
# Run with correct PORT in local/production
# ------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app", 
        host=settings.HOST, 
        port=settings.PORT,
        workers=1,  # Railway works better with single worker
        log_level=settings.LOG_LEVEL.lower()
    )
