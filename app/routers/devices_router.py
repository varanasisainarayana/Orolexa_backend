from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
import logging
from datetime import datetime

from ..db.session import get_session
from ..db.models.health.device import DeviceConnection
from ..db.models.users.user import User
from ..schemas.devices.device import DeviceConnectionCreate, DeviceConnectionResponse, DeviceStatus
from ..services.auth import decode_jwt_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/device", tags=["Device Management"])

oauth2_scheme = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    token = credentials.credentials
    payload = decode_jwt_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token: missing user ID")
    try:
        return int(user_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid token: invalid user ID format")


@router.get("/status", response_model=DeviceStatus)
def get_device_status(current_user: int = Depends(get_current_user), session: Session = Depends(get_session)):
    try:
        device_connection = session.exec(
            select(DeviceConnection)
            .where(DeviceConnection.user_id == current_user)
            .where(DeviceConnection.is_active == True)
            .order_by(DeviceConnection.connected_at.desc())
        ).first()
        if device_connection:
            return DeviceStatus(
                connected=True,
                device_id=device_connection.device_id,
                device_name=device_connection.device_name,
                ip_address=device_connection.ip_address,
                last_seen=device_connection.connected_at,
                battery_level=None,
                firmware_version=None,
            )
        else:
            return DeviceStatus(connected=False)
    except Exception as e:
        logger.error(f"Error getting device status for user {current_user}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get device status")


@router.post("/connect")
def connect_device(device_data: DeviceConnectionCreate, current_user: int = Depends(get_current_user), session: Session = Depends(get_session)):
    try:
        existing_connections = session.exec(
            select(DeviceConnection)
            .where(DeviceConnection.user_id == current_user)
            .where(DeviceConnection.is_active == True)
        ).all()
        for connection in existing_connections:
            connection.is_active = False
            connection.disconnected_at = datetime.utcnow()
            session.add(connection)

        device_connection = DeviceConnection(
            user_id=current_user,
            device_id=device_data.device_id,
            device_name=device_data.device_name,
            ip_address=device_data.ip_address,
            is_active=True,
        )
        session.add(device_connection)
        session.commit()
        session.refresh(device_connection)
        return {"success": True, "device_id": device_connection.device_id, "ip_address": device_connection.ip_address, "message": "Device connected successfully"}
    except Exception as e:
        logger.error(f"Error connecting device for user {current_user}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to connect device")


@router.post("/disconnect")
def disconnect_device(current_user: int = Depends(get_current_user), session: Session = Depends(get_session)):
    try:
        device_connection = session.exec(
            select(DeviceConnection)
            .where(DeviceConnection.user_id == current_user)
            .where(DeviceConnection.is_active == True)
        ).first()
        if not device_connection:
            return {"success": True, "message": "No active device connection to disconnect"}
        device_connection.is_active = False
        device_connection.disconnected_at = datetime.utcnow()
        session.add(device_connection)
        session.commit()
        return {"success": True, "message": "Device disconnected successfully"}
    except Exception as e:
        logger.error(f"Error disconnecting device for user {current_user}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to disconnect device")


@router.get("/connections", response_model=List[DeviceConnectionResponse])
def get_device_connections(current_user: int = Depends(get_current_user), session: Session = Depends(get_session)):
    try:
        device_connections = session.exec(
            select(DeviceConnection)
            .where(DeviceConnection.user_id == current_user)
            .order_by(DeviceConnection.connected_at.desc())
        ).all()
        return [
            DeviceConnectionResponse(
                id=c.id,
                device_id=c.device_id,
                device_name=c.device_name,
                ip_address=c.ip_address,
                connected_at=c.connected_at,
                disconnected_at=c.disconnected_at,
                is_active=c.is_active,
            )
            for c in device_connections
        ]
    except Exception as e:
        logger.error(f"Error retrieving device connections for user {current_user}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve device connections")


@router.delete("/connections/{connection_id}")
def delete_device_connection(connection_id: int, current_user: int = Depends(get_current_user), session: Session = Depends(get_session)):
    try:
        c = session.exec(
            select(DeviceConnection)
            .where(DeviceConnection.id == connection_id)
            .where(DeviceConnection.user_id == current_user)
        ).first()
        if not c:
            raise HTTPException(status_code=404, detail="Device connection not found")
        session.delete(c)
        session.commit()
        return {"success": True, "message": "Device connection deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting device connection {connection_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete device connection")


