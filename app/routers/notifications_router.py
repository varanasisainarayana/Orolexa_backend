from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
import logging
import json

from ..persistence.database import get_session
from ..models import Notification, User
from ..models.schemas import NotificationCreate, NotificationResponse, NotificationFilters
from ..utils import decode_jwt_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["Notifications"])

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


@router.get("/", response_model=List[NotificationResponse])
def get_notifications(
    type: Optional[str] = Query(None),
    read: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: int = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    try:
        query = select(Notification).where(Notification.user_id == current_user)
        if type:
            query = query.where(Notification.type == type)
        if read is not None:
            query = query.where(Notification.read == read)
        query = query.order_by(Notification.created_at.desc()).offset(offset).limit(limit)
        notifications = session.exec(query).all()

        result = []
        for n in notifications:
            data = None
            if n.data:
                try:
                    data = json.loads(n.data)
                except json.JSONDecodeError:
                    data = None
            result.append(NotificationResponse(
                id=n.id,
                type=n.type,
                title=n.title,
                message=n.message,
                data=data,
                read=n.read,
                created_at=n.created_at,
            ))
        return result
    except Exception as e:
        logger.error(f"Error retrieving notifications: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve notifications")


@router.get("/{notification_id}", response_model=NotificationResponse)
def get_notification(notification_id: int, current_user: int = Depends(get_current_user), session: Session = Depends(get_session)):
    try:
        n = session.exec(select(Notification).where(Notification.id == notification_id).where(Notification.user_id == current_user)).first()
        if not n:
            raise HTTPException(status_code=404, detail="Notification not found")
        data = None
        if n.data:
            try:
                data = json.loads(n.data)
            except json.JSONDecodeError:
                data = None
        return NotificationResponse(
            id=n.id,
            type=n.type,
            title=n.title,
            message=n.message,
            data=data,
            read=n.read,
            created_at=n.created_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving notification {notification_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve notification")


@router.put("/{notification_id}/read")
def mark_notification_read(notification_id: int, current_user: int = Depends(get_current_user), session: Session = Depends(get_session)):
    try:
        n = session.exec(select(Notification).where(Notification.id == notification_id).where(Notification.user_id == current_user)).first()
        if not n:
            raise HTTPException(status_code=404, detail="Notification not found")
        n.read = True
        session.add(n)
        session.commit()
        return {"success": True, "message": "Notification marked as read"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking notification {notification_id} as read: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to mark notification as read")


@router.put("/read-all")
def mark_all_notifications_read(current_user: int = Depends(get_current_user), session: Session = Depends(get_session)):
    try:
        unread = session.exec(select(Notification).where(Notification.user_id == current_user).where(Notification.read == False)).all()
        for n in unread:
            n.read = True
            session.add(n)
        session.commit()
        return {"success": True, "message": "All notifications marked as read", "updated_count": len(unread)}
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to mark notifications as read")


@router.delete("/{notification_id}")
def delete_notification(notification_id: int, current_user: int = Depends(get_current_user), session: Session = Depends(get_session)):
    try:
        n = session.exec(select(Notification).where(Notification.id == notification_id).where(Notification.user_id == current_user)).first()
        if not n:
            raise HTTPException(status_code=404, detail="Notification not found")
        session.delete(n)
        session.commit()
        return {"success": True, "message": "Notification deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting notification {notification_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete notification")


@router.post("/", response_model=NotificationResponse)
def create_notification(notification_data: NotificationCreate, current_user: int = Depends(get_current_user), session: Session = Depends(get_session)):
    try:
        data_json = json.dumps(notification_data.data) if notification_data.data else None
        n = Notification(user_id=current_user, type=notification_data.type, title=notification_data.title, message=notification_data.message, data=data_json, read=False)
        session.add(n)
        session.commit()
        session.refresh(n)
        return NotificationResponse(
            id=n.id,
            type=n.type,
            title=n.title,
            message=n.message,
            data=notification_data.data,
            read=n.read,
            created_at=n.created_at,
        )
    except Exception as e:
        logger.error(f"Error creating notification: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create notification")


