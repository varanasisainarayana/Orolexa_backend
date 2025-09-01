import os
from fastapi import FastAPI, HTTPException, Depends, File, UploadFile
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from datetime import datetime
import shutil
import mimetypes
import google.generativeai as genai
from sqlmodel import Session, select

from . import auth
from .database import create_db_and_tables, get_session
from .config import (
    ALLOWED_ORIGINS,
    TRUSTED_HOSTS,
    ESP32_MAX_IMAGE_SIZE,
    ESP32_MAX_IMAGES_PER_REQUEST,
    ESP32_ANALYSIS_TIMEOUT_MS,
    RATE_LIMIT_WINDOW_SEC,
    RATE_LIMIT_MAX_REQUESTS,
    DEBUG,
)
from .utils import decode_jwt_token
from .models import AnalysisHistory, User
from .schemas import (
    IPAddressRequest, StreamDataResponse, ESP32DataRequest, ESP32DeviceInfo, ESP32ImageUpload,
    ESP32ConnectionTestRequest, ESP32ConnectionTestResponse, ESP32ImageAnalysisRequest, 
    ESP32ImageAnalysisResponse, ESP32StreamStatusResponse, ESP32SessionRequest, 
    ESP32SessionResponse, ESP32ImageUploadRequest, ESP32ImageUploadResponse
)

# Load environment variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Validate essential envs in production
if not DEBUG and not os.getenv("GEMINI_API_KEY"):
    # Log only; endpoint usage will error explicitly when called
    pass

# Initialize FastAPI
app = FastAPI(title="Dental AI API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted hosts and optional HTTPS redirect (behind a proxy/ingress)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=TRUSTED_HOSTS)
if not DEBUG and os.getenv("ENABLE_HTTPS_REDIRECT", "true").lower() == "true":
    app.add_middleware(HTTPSRedirectMiddleware)

# Simple security headers
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=()"
    # HSTS only over HTTPS/production proxies
    if not DEBUG:
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    return response

# Centralized exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={
        "success": False,
        "message": exc.detail,
        "path": str(request.url)
    })

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={
        "success": False,
        "message": "Internal server error",
        "path": str(request.url)
    })

# ------------------------
# Simple in-memory rate limiting for ESP32 endpoints
# ------------------------
from collections import defaultdict, deque
import time as _time

_rate_buckets = defaultdict(lambda: deque())

def _rate_key(request: Request, user_id: int) -> str:
    client_ip = request.client.host if request.client else "unknown"
    return f"{user_id}:{client_ip}:{request.url.path}"

async def esp32_rate_limit(request: Request, current_user: int = Depends(lambda creds=Depends(HTTPBearer()): int(decode_jwt_token(creds.credentials).get("sub")) )):
    key = _rate_key(request, current_user)
    now = _time.time()
    window_start = now - RATE_LIMIT_WINDOW_SEC
    q = _rate_buckets[key]
    # drop old
    while q and q[0] < window_start:
        q.popleft()
    if len(q) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(status_code=429, detail="Too many requests from this client for this endpoint")
    q.append(now)
    return current_user

# Auth scheme
oauth2_scheme = HTTPBearer()

# Include authentication router
app.include_router(auth.router)

# DB setup on startup
@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# Dependency to get current user from JWT
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    token = credentials.credentials
    payload = decode_jwt_token(token)
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    try:
        return int(payload.get("sub"))  # user_id as int
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token subject")

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
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)

        saved_paths = []
        for f in [file1, file2, file3]:
            if not f:
                continue
            path = os.path.join(upload_dir, f"{datetime.utcnow().timestamp()}_{f.filename}")
            with open(path, "wb") as buffer:
                shutil.copyfileobj(f.file, buffer)
            saved_paths.append(path)

        return {
            "message": "Image(s) uploaded successfully",
            "file_paths": saved_paths,
            "uploaded_by": current_user
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ------------------------
# Analyze Images with Gemini (three inputs, only first required)
# ------------------------
@app.post("/analyze-image")
def analyze_image(
    file1: UploadFile = File(...),
    file2: UploadFile = File(None),
    file3: UploadFile = File(None),
    current_user: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    try:
        # Verify user exists
        user = session.exec(select(User).where(User.id == current_user)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        analyses = []
        saved_paths = []
        
        # Process each provided file
        for i, file in enumerate([file1, file2, file3], 1):
            if not file:
                continue
                
            # Save image
            upload_dir = "uploads"
            os.makedirs(upload_dir, exist_ok=True)
            image_path = os.path.join(upload_dir, f"{datetime.utcnow().timestamp()}_{file.filename}")
            with open(image_path, "wb") as f:
                f.write(file.file.read())
            saved_paths.append(image_path)

            # Detect MIME type
            mime_type, _ = mimetypes.guess_type(image_path)
            if not mime_type:
                mime_type = "image/jpeg"

            # Read image bytes
            with open(image_path, "rb") as img_file:
                image_bytes = img_file.read()

            # Gemini analysis
            model = genai.GenerativeModel("gemini-1.5-flash")
            result = model.generate_content(
                [
                    f"""You are a professional dental AI assistant. Analyze the provided dental image (image {i}) and provide a comprehensive assessment.

**Instructions:**
1. Examine the image carefully for dental health indicators
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

Please analyze the dental image and provide your assessment following these guidelines.""",
                    {
                        "mime_type": mime_type,
                        "data": image_bytes
                    }
                ]
            )

            analyses.append({
                "image_number": i,
                "analysis": result.text,
                "image_path": image_path
            })

            # Save analysis to DB
            report = AnalysisHistory(
                user_id=user.id,
                image_url=image_path,
                ai_report=result.text
            )
            session.add(report)

        session.commit()

        return {
            "message": f"Dental analysis completed for {len(analyses)} image(s)",
            "analyses": analyses,
            "total_images_analyzed": len(analyses)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ------------------------
# Get Analysis History
# ------------------------
@app.get("/history")
def get_history(
    current_user: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    reports = session.exec(
        select(AnalysisHistory)
        .where(AnalysisHistory.user_id == current_user)
        .order_by(AnalysisHistory.created_at.desc())
    ).all()

    return [
        {
            "id": r.id,
            "analysis": r.ai_report,
            "image_path": r.image_url,
            "timestamp": r.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }
        for r in reports
    ]

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
        uploads_dir = "uploads/profiles"
        os.makedirs(uploads_dir, exist_ok=True)
        ext = os.path.splitext(profile_photo.filename)[1]
        filename = f"{datetime.utcnow().timestamp()}_{profile_photo.filename}"
        saved_path = os.path.join(uploads_dir, filename)
        
        try:
            with open(saved_path, "wb") as f:
                shutil.copyfileobj(profile_photo.file, f)
            user.profile_photo_url = saved_path
        except Exception as e:
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
        
        # Test stream endpoint
        import requests
        try:
            stream_url = f"http://{request.ipAddress}:{request.port}{request.streamPath}"
            response = requests.get(stream_url, timeout=ESP32_STREAM_TIMEOUT_MS / 1000)
            stream_available = response.status_code == 200
        except:
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


@app.get("/api/esp32/stream-status/{device_id}")
def get_esp32_stream_status(
    device_id: str,
    current_user: int = Depends(get_current_user)
):
    """
    Get ESP32-CAM stream status
    """
    try:
        device_info = esp32_devices.get(device_id, {})
        
        return ESP32StreamStatusResponse(
            deviceId=device_id,
            isActive=device_info.get("status") == "online",
            lastSeen=device_info.get("last_seen", datetime.utcnow().isoformat()),
            streamQuality="good",
            connectionStats={
                "uptime": device_info.get("uptime", 0),
                "totalImages": len([img for img in esp32_images.values() if img.get("deviceId") == device_id]),
                "lastImageTime": device_info.get("last_image_time"),
                "averageResponseTime": 50
            },
            deviceInfo={
                "firmware": "ESP32-CAM v2.1.0",
                "model": "ESP32-CAM-MB",
                "resolution": "1600x1200",
                "frameRate": 30
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
            "port": request.port,
            "streamPath": request.streamPath
        }
        
        # Update device info
        esp32_devices[request.deviceId] = {
            "ip_address": request.ipAddress,
            "port": request.port,
            "stream_path": request.streamPath,
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
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
