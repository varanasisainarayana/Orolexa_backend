# app/services/device_service.py
from typing import List, Optional
from sqlmodel import Session, select
from datetime import datetime
import logging

from app.db.models import DeviceConnection
from app.schemas import DeviceConnectionCreate, DeviceStatus

logger = logging.getLogger(__name__)

class DeviceService:
    def __init__(self, session: Session):
        self.session = session

    def create_device_connection(self, device_data: DeviceConnectionCreate, user_id: str) -> Optional[DeviceConnection]:
        """Create new device connection"""
        try:
            device = DeviceConnection(
                user_id=user_id,
                **device_data.dict()
            )
            self.session.add(device)
            self.session.commit()
            self.session.refresh(device)
            return device
        except Exception as e:
            logger.error(f"Error creating device connection: {e}")
            self.session.rollback()
            return None

    def get_device_by_id(self, device_id: int) -> Optional[DeviceConnection]:
        """Get device connection by ID"""
        try:
            return self.session.exec(select(DeviceConnection).where(DeviceConnection.id == device_id)).first()
        except Exception as e:
            logger.error(f"Error getting device {device_id}: {e}")
            return None

    def get_user_devices(self, user_id: str) -> List[DeviceConnection]:
        """Get user's device connections"""
        try:
            return self.session.exec(
                select(DeviceConnection)
                .where(DeviceConnection.user_id == user_id)
                .order_by(DeviceConnection.connected_at.desc())
            ).all()
        except Exception as e:
            logger.error(f"Error getting user devices: {e}")
            return []

    def get_active_device(self, user_id: str) -> Optional[DeviceConnection]:
        """Get user's active device connection"""
        try:
            return self.session.exec(
                select(DeviceConnection)
                .where(
                    DeviceConnection.user_id == user_id,
                    DeviceConnection.is_active == True
                )
                .order_by(DeviceConnection.connected_at.desc())
            ).first()
        except Exception as e:
            logger.error(f"Error getting active device: {e}")
            return None

    def disconnect_device(self, device_id: int) -> bool:
        """Disconnect device"""
        try:
            device = self.get_device_by_id(device_id)
            if not device:
                return False
            
            device.is_active = False
            device.disconnected_at = datetime.utcnow()
            self.session.add(device)
            self.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error disconnecting device: {e}")
            self.session.rollback()
            return False

    def update_device_status(self, device_id: int, is_active: bool) -> bool:
        """Update device status"""
        try:
            device = self.get_device_by_id(device_id)
            if not device:
                return False
            
            device.is_active = is_active
            if not is_active:
                device.disconnected_at = datetime.utcnow()
            
            self.session.add(device)
            self.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating device status: {e}")
            self.session.rollback()
            return False

    def get_device_status(self, user_id: str) -> DeviceStatus:
        """Get device status for user"""
        try:
            active_device = self.get_active_device(user_id)
            
            if active_device:
                return DeviceStatus(
                    connected=True,
                    device_id=active_device.device_id,
                    device_name=active_device.device_name,
                    ip_address=active_device.ip_address,
                    last_seen=active_device.connected_at
                )
            else:
                return DeviceStatus(connected=False)
        except Exception as e:
            logger.error(f"Error getting device status: {e}")
            return DeviceStatus(connected=False)
