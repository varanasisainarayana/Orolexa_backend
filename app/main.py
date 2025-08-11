from fastapi import FastAPI, HTTPException, Depends, File, UploadFile
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from datetime import datetime
import os
import shutil
import mimetypes
import google.generativeai as genai
from typing import Union

from . import auth
from .database import create_db_and_tables, get_session
from .utils import decode_jwt_token
from .models import AnalysisHistory, User
from sqlmodel import Session, select

# Load environment variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Initialize FastAPI
app = FastAPI(title="Dental AI API")

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
# Upload Image (single)
# ------------------------
@app.post("/upload-image")
def upload_image(
    file: UploadFile = File(...),
    current_user: int = Depends(get_current_user)
):
    try:
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, f"{datetime.utcnow().timestamp()}_{file.filename}")

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return {
            "message": "Image uploaded successfully",
            "file_path": file_path,
            "uploaded_by": current_user
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ------------------------
# Analyze up to 3 images
# ------------------------
@app.post("/analyze-images")
async def analyze_images(
    file1: UploadFile = File(...),   # Required
    file2: UploadFile = File(None),  # Optional
    file3: UploadFile = File(None),  # Optional
    current_user: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    try:
        # Verify user exists
        user = session.exec(select(User).where(User.id == current_user)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Ensure uploads directory exists
        uploads_dir = "uploads"
        os.makedirs(uploads_dir, exist_ok=True)

        files = [f for f in [file1, file2, file3] if f is not None]
        results = []

        for uploaded in files:
            # Save file
            timestamped_name = f"{int(datetime.utcnow().timestamp()*1000)}_{uploaded.filename}"
            image_path = os.path.join(uploads_dir, timestamped_name)

            with open(image_path, "wb") as f:
                content = await uploaded.read()
                f.write(content)

            # Detect MIME type
            mime_type, _ = mimetypes.guess_type(image_path)
            if not mime_type:
                mime_type = "image/jpeg"

            # Read bytes
            with open(image_path, "rb") as img_f:
                image_bytes = img_f.read()

            # Gemini analysis
            prompt = (
                "You are a dental expert. Analyze this image for dental health, problems, "
                "and suggestions in simple terms for a patient. No styling, single paragraph."
            )
            model = genai.GenerativeModel("gemini-1.5-flash")
            result = model.generate_content(
                [
                    prompt,
                    {"mime_type": mime_type, "data": image_bytes}
                ]
            )
            analysis_text = result.text if hasattr(result, "text") else str(result)

            # Save analysis to DB
            report = AnalysisHistory(
                user_id=user.id,
                image_url=image_path,
                ai_report=analysis_text
            )
            session.add(report)
            session.commit()
            session.refresh(report)

            results.append({
                "filename": uploaded.filename,
                "saved_path": image_path,
                "analysis": analysis_text,
                "report_id": report.id
            })

        return {"message": "Dental analysis completed", "results": results}

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
