import os
from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.gzip import GZipMiddleware
from starlette.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from datetime import datetime
import shutil
import mimetypes
import google.generativeai as genai
from sqlmodel import Session, select
import logging
from collections import defaultdict, deque
import time as _time

# Load environment variables as early as possible
load_dotenv()

from .routers import auth_router
from .database import create_db_and_tables, get_session
from .config import (
    ESP32_MAX_IMAGE_SIZE,
    ESP32_MAX_IMAGES_PER_REQUEST,
    ESP32_ANALYSIS_TIMEOUT_MS,
    RATE_LIMIT_WINDOW_SEC,
    RATE_LIMIT_MAX_REQUESTS,
    DEBUG,
)
from .config import settings
from .middleware import RateLimitMiddleware, SecurityMiddleware, LoggingMiddleware, ErrorHandlingMiddleware, RequestSizeLimitMiddleware
from .exceptions import http_exception_handler
from .utils import decode_jwt_token
from .models import AnalysisHistory, User
from .schemas import (
    IPAddressRequest, ESP32DataRequest, ESP32DeviceInfo, ESP32ImageUpload,
    ESP32ConnectionTestRequest, ESP32ConnectionTestResponse, ESP32ImageAnalysisRequest, 
    ESP32ImageAnalysisResponse, ESP32SessionRequest, 
    ESP32SessionResponse, ESP32ImageUploadRequest, ESP32ImageUploadResponse
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
    app.state.db_init_ok = True
    app.state.db_init_error = None
    try:
        create_db_and_tables()
        
        # Optional: run Alembic upgrade if enabled
        if os.getenv("RUN_ALEMBIC_ON_STARTUP", "false").lower() in ("1", "true", "yes"): 
            try:
                import subprocess, sys
                logger.info("Running Alembic upgrade on startup...")
                subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
                logger.info("Alembic upgrade completed")
            except Exception as _e:
                logger.exception("Alembic upgrade failed")
        
        logger.info("Database initialized successfully")
    except Exception as e:
        # Do not crash the app; report via health endpoint
        app.state.db_init_ok = False
        app.state.db_init_error = str(e)
        logger.exception("Database initialization failed")
    yield
    # Shutdown
    logger.info("Shutting down Dental AI API...")

# Initialize FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
    docs_url=("/docs" if settings.DOCS_ENABLED else None),
    redoc_url=("/redoc" if settings.DOCS_ENABLED else None),
    openapi_url=("/openapi.json" if settings.DOCS_ENABLED else None)
)

# Add custom exception handler
app.add_exception_handler(HTTPException, http_exception_handler)

# Add middleware
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(SecurityMiddleware)
app.add_middleware(RequestSizeLimitMiddleware)
app.add_middleware(RateLimitMiddleware)

# GZip compression
app.add_middleware(GZipMiddleware, minimum_size=settings.GZIP_MIN_SIZE)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for uploaded images
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Auth scheme
oauth2_scheme = HTTPBearer(auto_error=False)

# Dependency to get current user from JWT
def get_current_user(request: Request, credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    token = None
    if credentials and credentials.credentials:
        token = credentials.credentials
    else:
        # Fallback to cookie
        token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    logger.info(f"Processing JWT token for authentication")
    payload = decode_jwt_token(token)
    if not payload:
        logger.warning("JWT token decode failed - invalid or expired token")
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user_id = payload.get("sub")
    if not user_id:
        logger.warning("JWT token missing user ID")
        raise HTTPException(status_code=401, detail="Invalid token: missing user ID")
    
    logger.info(f"Successfully authenticated user ID: {user_id}")
    return user_id

# ------------------------
# Simple in-memory rate limiting for ESP32 endpoints
# ------------------------
_rate_buckets = defaultdict(lambda: deque())

def _rate_key(request: Request, user_id: int) -> str:
    client_ip = request.client.host if request.client else "unknown"
    return f"{user_id}:{client_ip}:{request.url.path}"

def esp32_rate_limit(request: Request, current_user: int = Depends(get_current_user)):
    key = _rate_key(request, int(current_user) if current_user is not None else 0)
    now = _time.time()
    window_start = now - RATE_LIMIT_WINDOW_SEC
    q = _rate_buckets[key]
    while q and q[0] < window_start:
        q.popleft()
    if len(q) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(status_code=429, detail="Too many requests from this client for this endpoint")
    q.append(now)
    return int(current_user) if current_user is not None else 0

# Include authentication router
app.include_router(auth_router.router)

# Include all routers
from .routers import analysis_router
from .routers import doctors_router
from .routers import appointments_router
from .routers import notifications_router
from .routers import devices_router
from .routers import health_analytics_router
from .routers import settings_router
# Streaming removed - implemented in frontend

app.include_router(analysis_router.router)
app.include_router(doctors_router.router)
app.include_router(appointments_router.router)
app.include_router(notifications_router.router)
app.include_router(devices_router.router)
app.include_router(health_analytics_router.router)
app.include_router(settings_router.router)

# Health check endpoint
@app.get("/health")
def health_check():
    return {
        "status": "healthy" if getattr(app.state, "db_init_ok", True) else "degraded",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.utcnow().isoformat(),
        "environment": "railway" if settings.RAILWAY_ENVIRONMENT else "local",
        "port": settings.PORT,
        "database": {
            "ok": getattr(app.state, "db_init_ok", True),
            "error": getattr(app.state, "db_init_error", None)
        },
        "auth": {
            "secret_key_configured": bool(settings.SECRET_KEY and settings.SECRET_KEY != "change-me-in-prod"),
            "jwt_algorithm": settings.ALGORITHM,
            "token_expiry_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES
        }
    }





# ------------------------
# Upload Images (three inputs, only first required)
# ------------------------
@app.post("/upload-image")
def upload_image(
    file1: UploadFile = File(None),
    file2: UploadFile = File(None),
    file3: UploadFile = File(None),
    current_user: str = Depends(get_current_user)
):
    try:
        upload_dir = settings.UPLOAD_DIR
        os.makedirs(upload_dir, exist_ok=True)

        files = [f for f in [file1, file2, file3] if f is not None]
        if not files:
            raise HTTPException(status_code=400, detail="At least one file must be uploaded.")

        saved_paths = []
        for f in files:
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
    
    # Build profile photo URL
    profile_photo_url = None
    if user.profile_photo_url:
        if user.profile_photo_url.startswith("http"):
            profile_photo_url = user.profile_photo_url
        else:
            profile_photo_url = f"{settings.BASE_URL}/{user.profile_photo_url}"
    
    return {
        "success": True,
        "data": {
            "id": user.id,
            "full_name": user.full_name,
            "mobile_number": user.mobile_number,
            "profile_photo_url": profile_photo_url,
            "created_at": user.created_at.isoformat()
        },
        "error": None
    }

# ------------------------
# Test Authentication Endpoint
# ------------------------
@app.get("/test-auth")
def test_auth(current_user: int = Depends(get_current_user)):
    """Test endpoint to verify authentication is working"""
    return {
        "success": True,
        "message": "Authentication successful",
        "user_id": current_user,
        "timestamp": datetime.utcnow().isoformat()
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
    
    # Build profile photo URL
    profile_photo_url = None
    if user.profile_photo_url:
        if user.profile_photo_url.startswith("http"):
            profile_photo_url = user.profile_photo_url
        else:
            profile_photo_url = f"{settings.BASE_URL}/{user.profile_photo_url}"
    
    return {
        "success": True,
        "data": {
            "id": user.id,
            "full_name": user.full_name,
            "mobile_number": user.mobile_number,
            "profile_photo_url": profile_photo_url,
            "created_at": user.created_at.isoformat()
        },
        "error": None
    }

# ------------------------
# ESP32-CAM API Endpoints
# ------------------------

# In-memory storage for ESP32 devices and sessions
esp32_devices = {}
esp32_sessions = {}
esp32_images = {}
esp32_analysis = {}

@app.post("/api/esp32/test-connection")
def test_esp32_connection(
    request: ESP32ConnectionTestRequest,
    current_user: int = Depends(get_current_user),
    _rl: int = Depends(esp32_rate_limit),
):
    """
    Test connection to ESP32-CAM device
    """
    try:
        import socket
        import time
        
        start_time = time.time()
        
        # Test basic connectivity
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((request.ipAddress, request.port))
        sock.close()
        
        if result != 0:
            return ESP32ConnectionTestResponse(
                success=False,
                message="Connection failed",
                error="Device not reachable"
            )
        
        # Test stream endpoint (removed - streaming handled in frontend)
        stream_available = False
        
        response_time = int((time.time() - start_time) * 1000)
        
        return ESP32ConnectionTestResponse(
            success=True,
            message="ESP32-CAM connection successful",
            connectionDetails={
                "isReachable": True,
                "responseTime": response_time,
                "streamAvailable": stream_available,
                "lastChecked": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        return ESP32ConnectionTestResponse(
            success=False,
            message="Connection test failed",
            error=str(e)
        )


@app.post("/api/esp32/analyze-images")
def analyze_esp32_images(
    request: ESP32ImageAnalysisRequest,
    current_user: int = Depends(get_current_user),
    _rl: int = Depends(esp32_rate_limit),
):
    """
    Analyze images from ESP32-CAM using Gemini AI
    """
    try:
        analysis_id = f"analysis_{int(datetime.utcnow().timestamp())}"
        start_time = datetime.utcnow()
        
        # Validate images
        if len(request.images) == 0:
            raise HTTPException(status_code=400, detail="No images provided")
        if len(request.images) > ESP32_MAX_IMAGES_PER_REQUEST:
            raise HTTPException(status_code=400, detail=f"Maximum {ESP32_MAX_IMAGES_PER_REQUEST} images allowed per request")
        
        # Process images with Gemini AI
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        # Convert base64 images to bytes for Gemini
        image_parts = []
        for i, base64_img in enumerate(request.images):
            try:
                import base64
                # Remove data:image/jpeg;base64, prefix if present
                if ',' in base64_img:
                    base64_img = base64_img.split(',')[1]
                
                image_bytes = base64.b64decode(base64_img)
                if len(image_bytes) > ESP32_MAX_IMAGE_SIZE:
                    raise HTTPException(status_code=413, detail="Image too large")
                image_parts.append({
                    "mime_type": "image/jpeg",
                    "data": image_bytes
                })
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid image {i+1}: {str(e)}")
        
        # Create analysis prompt
        analysis_type = request.analysisPreferences.get("analysisType", "dental") if request.analysisPreferences else "dental"
        
        if analysis_type == "dental":
            prompt = """You are a professional dental AI assistant. Analyze the provided dental images and provide a comprehensive assessment.

**Instructions:**
1. Examine each image carefully for dental health indicators
2. Provide a detailed analysis in a professional, medical tone
3. Focus on both positive aspects and areas of concern
4. Be specific about tooth locations and conditions
5. Provide actionable recommendations when appropriate

**Analysis Structure:**
Please provide your analysis in the following format:

**Overall Assessment:**
[Brief summary of dental health status]
Also give overall rating of the dental health of the patient out of 5.

**Detailed Findings:**
- [Specific observations about teeth, gums, and oral health]
- [Note any visible issues like cavities, discoloration, gaps, etc.]
- [Comment on gum health and overall oral hygiene]

**Areas of Concern:**
- [List any detected issues or potential problems]
- [Specify severity and urgency if applicable]

**Positive Aspects:**
- [Highlight good dental health indicators]
- [Note healthy teeth, gums, or good oral hygiene signs]

**Recommendations:**
- [Suggest specific actions or lifestyle changes]
- [Mention if professional dental consultation is recommended]
- [Provide preventive care advice]

**Important Notes:**
- If the image quality is poor or unclear, mention this limitation
- If the image doesn't show teeth clearly, state this clearly
- Be encouraging but honest about any concerns
- Use professional medical terminology appropriately
- Keep the tone helpful and educational

**Response Guidelines:**
- Keep the total response between 200-400 words
- Use clear, easy-to-understand language
- Be specific about tooth locations (e.g., "upper right molar", "lower left incisor")
- If no teeth are visible, clearly state this
- Focus on what can be observed from the image

Please analyze the dental images and provide your assessment following these guidelines."""
        else:
            prompt = f"Analyze the provided images for {analysis_type} purposes. Provide detailed observations and recommendations."
        
        # Generate analysis
        result = model.generate_content([prompt] + image_parts)
        
        # Process results
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        # Store analysis results
        esp32_analysis[analysis_id] = {
            "status": "completed",
            "results": {
                "analysis": result.text,
                "imageCount": len(request.images),
                "analysisType": analysis_type
            },
            "processingTime": processing_time,
            "timestamp": datetime.utcnow().isoformat(),
            "userId": current_user,
            "metadata": request.metadata
        }
        
        return ESP32ImageAnalysisResponse(
            status="completed",
            analysisId=analysis_id,
            results={
                "overallHealth": "good",  # This could be extracted from AI response
                "detectedIssues": [],
                "recommendations": [],
                "summary": result.text[:200] + "..." if len(result.text) > 200 else result.text,
                "riskScore": 25
            },
            processingTime=processing_time,
            timestamp=datetime.utcnow().isoformat(),
            nextSteps=[
                "Continue regular oral hygiene",
                "Schedule dental appointment",
                "Monitor for any changes"
            ]
        )
        
    except Exception as e:
        return ESP32ImageAnalysisResponse(
            status="failed",
            analysisId=f"analysis_{int(datetime.utcnow().timestamp())}",
            processingTime=0,
            timestamp=datetime.utcnow().isoformat(),
            error=str(e)
        )


# Streaming status endpoint removed - handled entirely in frontend


@app.post("/api/esp32/sessions")
def create_esp32_session(
    request: ESP32SessionRequest,
    current_user: int = Depends(get_current_user)
):
    """
    Create a new ESP32-CAM session
    """
    try:
        session_id = f"session_{int(datetime.utcnow().timestamp())}"
        
        # Store session
        esp32_sessions[session_id] = {
            "sessionId": session_id,
            "deviceId": request.deviceId,
            "status": "active",
            "startTime": datetime.utcnow().isoformat(),
            "totalImages": 0,
            "analysisCount": 0,
            "userId": current_user,
            "sessionType": request.sessionType.value,
            "ipAddress": request.ipAddress,
            "port": request.port
        }
        
        # Update device info
        esp32_devices[request.deviceId] = {
            "ip_address": request.ipAddress,
            "port": request.port,
            "status": "online",
            "last_seen": datetime.utcnow().isoformat(),
            "session_id": session_id
        }
        
        return ESP32SessionResponse(
            sessionId=session_id,
            deviceId=request.deviceId,
            status="active",
            startTime=datetime.utcnow().isoformat(),
            totalImages=0,
            analysisCount=0,
            sessionUrl=f"/api/esp32/sessions/{session_id}"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/esp32/upload-image")
def upload_esp32_image(
    request: ESP32ImageUploadRequest,
    current_user: int = Depends(get_current_user),
    _rl: int = Depends(esp32_rate_limit),
):
    """
    Upload image from ESP32-CAM
    """
    try:
        image_id = f"img_{int(datetime.utcnow().timestamp())}"
        
        # Validate session
        if request.sessionId not in esp32_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Save image
        upload_dir = "uploads/esp32_images"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Decode base64 image
        import base64
        if ',' in request.image:
            image_data = base64.b64decode(request.image.split(',')[1])
        else:
            image_data = base64.b64decode(request.image)
        if len(image_data) > ESP32_MAX_IMAGE_SIZE:
            raise HTTPException(status_code=413, detail="Image too large")
        
        # Generate filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"esp32_{request.deviceId}_{timestamp}.{request.imageType}"
        filepath = os.path.join(upload_dir, filename)
        
        # Save image
        with open(filepath, "wb") as f:
            f.write(image_data)
        
        # Store image info
        esp32_images[image_id] = {
            "imageId": image_id,
            "sessionId": request.sessionId,
            "deviceId": request.deviceId,
            "url": filepath,
            "imageType": request.imageType,
            "timestamp": request.timestamp,
            "metadata": request.metadata or {}
        }
        
        # Update session
        if request.sessionId in esp32_sessions:
            esp32_sessions[request.sessionId]["totalImages"] += 1
        
        # Update device
        if request.deviceId in esp32_devices:
            esp32_devices[request.deviceId]["last_image_time"] = datetime.utcnow().isoformat()
        
        return ESP32ImageUploadResponse(
            success=True,
            imageId=image_id,
            url=filepath,
            message="Image uploaded successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/esp32/sessions/{session_id}")
def get_esp32_session(
    session_id: str,
    current_user: int = Depends(get_current_user)
):
    """
    Get ESP32-CAM session details
    """
    try:
        if session_id not in esp32_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = esp32_sessions[session_id]
        
        # Get images for this session
        session_images = [img for img in esp32_images.values() if img.get("sessionId") == session_id]
        
        return {
            **session,
            "images": session_images,
            "imageCount": len(session_images)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/esp32/devices")
def get_esp32_devices(
    current_user: int = Depends(get_current_user)
):
    """
    Get all ESP32 devices
    """
    try:
        return {
            "devices": esp32_devices,
            "total_devices": len(esp32_devices),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/esp32/analysis/{analysis_id}")
def get_esp32_analysis(
    analysis_id: str,
    current_user: int = Depends(get_current_user)
):
    """
    Get ESP32-CAM analysis results
    """
    try:
        if analysis_id not in esp32_analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        return esp32_analysis[analysis_id]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
