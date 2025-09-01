# app/notifications.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
import logging
import json
from datetime import datetime

from .database import get_session
from .models import Notification, User
from .schemas import NotificationCreate, NotificationResponse, NotificationFilters
from .utils import decode_jwt_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["Notifications"])

# Auth scheme
oauth2_scheme = HTTPBearer()

# Dependency to get current user from JWT
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

@router.get("/", response_model=List[NotificationResponse])
def get_notifications(
    type: Optional[str] = Query(None, description="Filter by notification type"),
    read: Optional[bool] = Query(None, description="Filter by read status"),
    limit: int = Query(50, ge=1, le=100, description="Number of notifications to return"),
    offset: int = Query(0, ge=0, description="Number of notifications to skip"),
    current_user: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get user notifications with optional filtering and pagination"""
    try:
        # Build query
        query = select(Notification).where(Notification.user_id == current_user)
        
        # Apply filters
        if type:
            query = query.where(Notification.type == type)
        
        if read is not None:
            query = query.where(Notification.read == read)
        
        # Apply pagination and ordering
        query = query.order_by(Notification.created_at.desc()).offset(offset).limit(limit)
        
        notifications = session.exec(query).all()
        
        logger.info(f"Retrieved {len(notifications)} notifications for user {current_user}")
        
        result = []
        for notification in notifications:
            # Parse data JSON if it exists
            data = None
            if notification.data:
                try:
                    data = json.loads(notification.data)
                except json.JSONDecodeError:
                    data = None
            
            result.append(NotificationResponse(
                id=notification.id,
                type=notification.type,
                title=notification.title,
                message=notification.message,
                data=data,
                read=notification.read,
                created_at=notification.created_at
            ))
        
        return result
        
    except Exception as e:
        logger.error(f"Error retrieving notifications: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve notifications")

@router.get("/{notification_id}", response_model=NotificationResponse)
def get_notification(
    notification_id: int,
    current_user: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get specific notification by ID"""
    try:
        notification = session.exec(
            select(Notification)
            .where(Notification.id == notification_id)
            .where(Notification.user_id == current_user)
        ).first()
        
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        # Parse data JSON if it exists
        data = None
        if notification.data:
            try:
                data = json.loads(notification.data)
            except json.JSONDecodeError:
                data = None
        
        return NotificationResponse(
            id=notification.id,
            type=notification.type,
            title=notification.title,
            message=notification.message,
            data=data,
            read=notification.read,
            created_at=notification.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving notification {notification_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve notification")

@router.put("/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    current_user: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Mark a notification as read"""
    try:
        notification = session.exec(
            select(Notification)
            .where(Notification.id == notification_id)
            .where(Notification.user_id == current_user)
        ).first()
        
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        notification.read = True
        session.add(notification)
        session.commit()
        
        logger.info(f"Marked notification {notification_id} as read by user {current_user}")
        
        return {"success": True, "message": "Notification marked as read"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking notification {notification_id} as read: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to mark notification as read")

@router.put("/read-all")
def mark_all_notifications_read(
    current_user: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Mark all notifications as read"""
    try:
        # Get all unread notifications for the user
        unread_notifications = session.exec(
            select(Notification)
            .where(Notification.user_id == current_user)
            .where(Notification.read == False)
        ).all()
        
        # Mark all as read
        for notification in unread_notifications:
            notification.read = True
            session.add(notification)
        
        session.commit()
        
        logger.info(f"Marked {len(unread_notifications)} notifications as read by user {current_user}")
        
        return {
            "success": True,
            "message": "All notifications marked as read",
            "updated_count": len(unread_notifications)
        }
        
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to mark notifications as read")

@router.delete("/{notification_id}")
def delete_notification(
    notification_id: int,
    current_user: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Delete a notification"""
    try:
        notification = session.exec(
            select(Notification)
            .where(Notification.id == notification_id)
            .where(Notification.user_id == current_user)
        ).first()
        
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        session.delete(notification)
        session.commit()
        
        logger.info(f"Deleted notification {notification_id} by user {current_user}")
        
        return {"success": True, "message": "Notification deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting notification {notification_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete notification")

@router.post("/", response_model=NotificationResponse)
def create_notification(
    notification_data: NotificationCreate,
    current_user: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Create a new notification (for internal use)"""
    try:
        # Convert data dict to JSON string
        data_json = None
        if notification_data.data:
            data_json = json.dumps(notification_data.data)
        
        notification = Notification(
            user_id=current_user,
            type=notification_data.type,
            title=notification_data.title,
            message=notification_data.message,
            data=data_json,
            read=False
        )
        
        session.add(notification)
        session.commit()
        session.refresh(notification)
        
        logger.info(f"Created notification {notification.id} for user {current_user}")
        
        return NotificationResponse(
            id=notification.id,
            type=notification.type,
            title=notification.title,
            message=notification.message,
            data=notification_data.data,
            read=notification.read,
            created_at=notification.created_at
        )
        
    except Exception as e:
        logger.error(f"Error creating notification: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create notification")

# Utility function to create notifications for other parts of the app
def create_user_notification(
    session: Session,
    user_id: int,
    notification_type: str,
    title: str,
    message: str,
    data: Optional[dict] = None
) -> Notification:
    """Utility function to create notifications from other parts of the app"""
    try:
        data_json = json.dumps(data) if data else None
        
        notification = Notification(
            user_id=user_id,
            type=notification_type,
            title=title,
            message=message,
            data=data_json,
            read=False
        )
        
        session.add(notification)
        session.commit()
        session.refresh(notification)
        
        logger.info(f"Created {notification_type} notification {notification.id} for user {user_id}")
        
        return notification
        
    except Exception as e:
        logger.error(f"Error creating notification for user {user_id}: {str(e)}")
        raise
