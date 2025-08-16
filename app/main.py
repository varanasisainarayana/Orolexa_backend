import os
from fastapi import FastAPI, HTTPException, Depends, File, UploadFile
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from datetime import datetime
import shutil
import mimetypes
import google.generativeai as genai
from sqlmodel import Session, select

from . import auth
from .database import create_db_and_tables, get_session
from .utils import decode_jwt_token
from .models import AnalysisHistory, User

# Load environment variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Configure base URL for image serving
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# Initialize FastAPI
app = FastAPI(title="Dental AI API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for uploaded images
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Auth scheme
oauth2_scheme = HTTPBearer()

# Include authentication router
app.include_router(auth.router)

# DB setup on startup
@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# Health check endpoint
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Dental AI API",
        "timestamp": datetime.utcnow().isoformat()
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
            "success": True,
            "data": {
                "message": "Images uploaded successfully",
                "file_paths": saved_paths,
                "uploaded_by": current_user,
                "total_images": len(saved_paths)
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

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

        saved_paths = []
        image_data = []
        
        # Process each provided file
        for i, file in enumerate([file1, file2, file3], 1):
            if not file:
                continue
            
            # Validate file type
            if not file.content_type or not file.content_type.startswith('image/'):
                raise HTTPException(status_code=415, detail=f"File {i} is not a valid image")
            
            # Validate file size (10MB limit)
            file.file.seek(0, 2)  # Seek to end
            file_size = file.file.tell()
            file.file.seek(0)  # Reset to beginning
            
            if file_size > 10 * 1024 * 1024:  # 10MB
                raise HTTPException(status_code=413, detail=f"File {i} is too large (max 10MB)")
                
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
            
            image_data.append({
                "mime_type": mime_type,
                "data": image_bytes,
                "path": image_path
            })

        # Unified Gemini analysis for all images
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        # Prepare content for analysis
        content = [
            f"""You are a professional dental AI assistant. Analyze the provided dental images ({len(image_data)} total) and provide a comprehensive unified assessment.

**Instructions:**
1. Examine all images together for a complete dental health picture
2. Provide a unified analysis that considers all angles and views
3. Use professional, medical tone while being encouraging
4. Be specific about tooth locations and conditions across all images
5. Provide actionable recommendations based on the complete assessment

**Analysis Structure:**
Please provide your analysis in the following format:

**Overall Assessment:**
[Comprehensive summary considering all images - mention how many images were analyzed]
Overall dental health rating out of 5.

**Detailed Findings:**
- [Specific observations about teeth, gums, and oral health from all angles]
- [Note any visible issues like cavities, discoloration, gaps, etc.]
- [Comment on gum health and overall oral hygiene across all views]

**Areas of Concern:**
- [List any detected issues or potential problems from any image]
- [Specify severity and urgency if applicable]
- [Mention if issues are visible from multiple angles]

**Positive Aspects:**
- [Highlight good dental health indicators from all images]
- [Note healthy teeth, gums, or good oral hygiene signs]

**Recommendations:**
- [Suggest specific actions or lifestyle changes]
- [Mention if professional dental consultation is recommended]
- [Provide preventive care advice based on complete assessment]

**Important Notes:**
- If any image quality is poor or unclear, mention this limitation
- If some images don't show teeth clearly, state this clearly
- Be encouraging but honest about any concerns
- Use professional medical terminology appropriately
- Keep the tone helpful and educational

**Response Guidelines:**
- Keep the total response between 300-600 words (longer for multiple images)
- Use clear, easy-to-understand language
- Be specific about tooth locations (e.g., "upper right molar", "lower left incisor")
- If no teeth are visible in any image, clearly state this
- Focus on what can be observed from all images combined

Please analyze all {len(image_data)} dental image(s) and provide your unified assessment following these guidelines."""
        ]
        
        # Add all images to the content
        for i, img in enumerate(image_data, 1):
            content.append({
                "mime_type": img["mime_type"],
                "data": img["data"]
            })

        result = model.generate_content(content)

        # Save unified analysis to DB
        report = AnalysisHistory(
            user_id=user.id,
            image_url=",".join(saved_paths),  # Store all image paths
            ai_report=result.text
        )
        session.add(report)
        session.commit()

        # Generate public URLs for images
        image_urls = [f"{BASE_URL}/{path}" for path in saved_paths]

        return {
            "success": True,
            "data": {
                "message": f"Unified dental analysis completed for {len(image_data)} image(s)",
                "analysis": {
                    "image_paths": image_urls,
                    "analysis": result.text,
                    "total_images_analyzed": len(image_data)
                }
            }
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# ------------------------
# Get Analysis History
# ------------------------
@app.get("/history")
def get_history(
    current_user: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    try:
        reports = session.exec(
            select(AnalysisHistory)
            .where(AnalysisHistory.user_id == current_user)
            .order_by(AnalysisHistory.created_at.desc())
        ).all()

        history_data = []
        for r in reports:
            image_paths = r.image_url.split(",") if "," in r.image_url else [r.image_url]
            image_urls = [f"{BASE_URL}/{path}" for path in image_paths]
            
            history_data.append({
                "id": r.id,
                "analysis": r.ai_report,
                "image_paths": image_urls,
                "total_images": len(image_paths),
                "timestamp": r.created_at.strftime("%Y-%m-%d %H:%M:%S")
            })

        return {
            "success": True,
            "data": history_data
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

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
# Run with correct PORT in local/production
# ------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
