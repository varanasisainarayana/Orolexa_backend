import os
from fastapi import FastAPI, HTTPException, Depends, File, UploadFile
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
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
# Run with correct PORT in local/production
# ------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
