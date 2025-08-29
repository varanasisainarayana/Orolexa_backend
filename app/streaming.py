# app/streaming.py
import asyncio
import cv2
import numpy as np
import aiohttp
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.responses import StreamingResponse
import io
from PIL import Image
import base64
from .utils import decode_jwt_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .config import settings

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/streaming", tags=["Streaming"])

# Auth scheme
oauth2_scheme = HTTPBearer(auto_error=False)

# Store active connections
active_connections: Dict[str, WebSocket] = {}

# ESP32 Camera configuration
class ESP32CameraConfig:
    def __init__(self, ip_address: str, port: int = 80):
        self.ip_address = ip_address
        self.port = port
        self.base_url = f"http://{ip_address}:{port}"
        self.stream_url = f"{self.base_url}/stream"
        self.snapshot_url = f"{self.base_url}/capture"
        self.is_connected = False

# Global ESP32 camera instance
esp32_camera: Optional[ESP32CameraConfig] = None

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    """Dependency to get current user from JWT"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    payload = decode_jwt_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token: missing user ID")
    
    return user_id

@router.post("/setup-camera")
async def setup_esp32_camera(
    ip_address: str,
    port: int = 80,
    current_user: str = Depends(get_current_user)
):
    """
    Setup ESP32 camera connection
    """
    global esp32_camera
    
    try:
        esp32_camera = ESP32CameraConfig(ip_address, port)
        
        # Test connection
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{esp32_camera.base_url}/") as response:
                if response.status == 200:
                    esp32_camera.is_connected = True
                    logger.info(f"ESP32 camera connected at {esp32_camera.base_url}")
                else:
                    raise HTTPException(status_code=400, detail="Cannot connect to ESP32 camera")
        
        return {
            "success": True,
            "message": f"ESP32 camera connected successfully at {esp32_camera.base_url}",
            "camera_url": esp32_camera.base_url,
            "stream_url": esp32_camera.stream_url,
            "snapshot_url": esp32_camera.snapshot_url
        }
    
    except Exception as e:
        logger.error(f"Failed to setup ESP32 camera: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to setup camera: {str(e)}")

@router.get("/camera-status")
async def get_camera_status(current_user: str = Depends(get_current_user)):
    """
    Get current ESP32 camera status
    """
    global esp32_camera
    
    if not esp32_camera:
        return {
            "success": False,
            "message": "No ESP32 camera configured",
            "is_connected": False
        }
    
    # Test connection
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{esp32_camera.base_url}/", timeout=5) as response:
                esp32_camera.is_connected = response.status == 200
    except Exception:
        esp32_camera.is_connected = False
    
    return {
        "success": True,
        "is_connected": esp32_camera.is_connected,
        "camera_url": esp32_camera.base_url,
        "stream_url": esp32_camera.stream_url,
        "snapshot_url": esp32_camera.snapshot_url
    }

@router.websocket("/ws-stream")
async def websocket_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time video streaming
    """
    await websocket.accept()
    connection_id = f"stream_{id(websocket)}"
    active_connections[connection_id] = websocket
    
    logger.info(f"WebSocket connection established: {connection_id}")
    
    try:
        while True:
            if not esp32_camera or not esp32_camera.is_connected:
                await websocket.send_text("Camera not connected")
                await asyncio.sleep(1)
                continue
            
            # Capture frame from ESP32 camera
            frame = await capture_frame_from_esp32()
            if frame is not None:
                # Convert frame to base64
                frame_base64 = frame_to_base64(frame)
                await websocket.send_text(frame_base64)
            
            await asyncio.sleep(0.1)  # 10 FPS
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        if connection_id in active_connections:
            del active_connections[connection_id]

@router.get("/snapshot")
async def get_snapshot(current_user: str = Depends(get_current_user)):
    """
    Get a single snapshot from ESP32 camera
    """
    global esp32_camera
    
    if not esp32_camera or not esp32_camera.is_connected:
        raise HTTPException(status_code=400, detail="ESP32 camera not connected")
    
    try:
        frame = await capture_frame_from_esp32()
        if frame is None:
            raise HTTPException(status_code=500, detail="Failed to capture frame")
        
        # Convert frame to JPEG
        _, buffer = cv2.imencode('.jpg', frame)
        image_bytes = buffer.tobytes()
        
        return StreamingResponse(
            io.BytesIO(image_bytes),
            media_type="image/jpeg",
            headers={"Cache-Control": "no-cache"}
        )
    
    except Exception as e:
        logger.error(f"Failed to get snapshot: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get snapshot: {str(e)}")

@router.get("/stream")
async def stream_video(current_user: str = Depends(get_current_user)):
    """
    Stream video from ESP32 camera using Server-Sent Events
    """
    global esp32_camera
    
    if not esp32_camera or not esp32_camera.is_connected:
        raise HTTPException(status_code=400, detail="ESP32 camera not connected")
    
    async def generate_frames():
        while True:
            try:
                frame = await capture_frame_from_esp32()
                if frame is not None:
                    # Convert frame to JPEG
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    frame_bytes = buffer.tobytes()
                    
                    # Send frame as multipart response
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                
                await asyncio.sleep(0.1)  # 10 FPS
                
            except Exception as e:
                logger.error(f"Error in video stream: {str(e)}")
                break
    
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache"}
    )

async def capture_frame_from_esp32() -> Optional[np.ndarray]:
    """
    Capture a frame from ESP32 camera
    """
    global esp32_camera
    
    if not esp32_camera:
        return None
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(esp32_camera.snapshot_url, timeout=10) as response:
                if response.status == 200:
                    image_data = await response.read()
                    
                    # Convert bytes to numpy array
                    nparr = np.frombuffer(image_data, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    
                    if frame is not None:
                        # Resize frame for better performance
                        frame = cv2.resize(frame, (640, 480))
                        return frame
                    
    except Exception as e:
        logger.error(f"Failed to capture frame from ESP32: {str(e)}")
    
    return None

def frame_to_base64(frame: np.ndarray) -> str:
    """
    Convert OpenCV frame to base64 string
    """
    try:
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Convert to PIL Image
        pil_image = Image.fromarray(frame_rgb)
        
        # Convert to base64
        buffer = io.BytesIO()
        pil_image.save(buffer, format='JPEG', quality=80)
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/jpeg;base64,{img_str}"
    
    except Exception as e:
        logger.error(f"Failed to convert frame to base64: {str(e)}")
        return ""

@router.post("/analyze-stream")
async def analyze_stream_frame(current_user: str = Depends(get_current_user)):
    """
    Capture a frame from ESP32 camera and analyze it using the dental AI
    """
    global esp32_camera
    
    if not esp32_camera or not esp32_camera.is_connected:
        raise HTTPException(status_code=400, detail="ESP32 camera not connected")
    
    try:
        # Capture frame
        frame = await capture_frame_from_esp32()
        if frame is None:
            raise HTTPException(status_code=500, detail="Failed to capture frame from camera")
        
        # Convert frame to bytes for analysis
        _, buffer = cv2.imencode('.jpg', frame)
        image_bytes = buffer.tobytes()
        
        # Here you would integrate with your existing analysis endpoints
        # For now, return the captured frame info
        return {
            "success": True,
            "message": "Frame captured successfully",
            "frame_size": frame.shape,
            "image_bytes_length": len(image_bytes),
            "camera_url": esp32_camera.base_url
        }
    
    except Exception as e:
        logger.error(f"Failed to analyze stream frame: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze frame: {str(e)}")

@router.delete("/disconnect-camera")
async def disconnect_camera(current_user: str = Depends(get_current_user)):
    """
    Disconnect ESP32 camera
    """
    global esp32_camera
    
    if esp32_camera:
        esp32_camera.is_connected = False
        esp32_camera = None
        logger.info("ESP32 camera disconnected")
    
    return {
        "success": True,
        "message": "ESP32 camera disconnected successfully"
    }
