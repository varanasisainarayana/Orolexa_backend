# app/services/user_service.py
from typing import Optional, List
from sqlmodel import Session, select
from datetime import datetime
import logging

from app.db.models import User
from app.schemas import UserResponse, UpdateProfileRequest

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self, session: Session):
        self.session = session

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            return self.session.exec(select(User).where(User.id == user_id)).first()
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {e}")
            return None

    def get_user_by_phone(self, phone: str) -> Optional[User]:
        """Get user by phone number"""
        try:
            return self.session.exec(select(User).where(User.phone == phone)).first()
        except Exception as e:
            logger.error(f"Error getting user by phone {phone}: {e}")
            return None

    def create_user(self, user_data: dict) -> Optional[User]:
        """Create new user"""
        try:
            user = User(**user_data)
            self.session.add(user)
            self.session.commit()
            self.session.refresh(user)
            return user
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            self.session.rollback()
            return None

    def update_user(self, user_id: str, update_data: dict) -> Optional[User]:
        """Update user"""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return None
            
            for key, value in update_data.items():
                if hasattr(user, key) and value is not None:
                    setattr(user, key, value)
            
            user.updated_at = datetime.utcnow()
            self.session.add(user)
            self.session.commit()
            self.session.refresh(user)
            return user
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            self.session.rollback()
            return None

    def delete_user(self, user_id: str) -> bool:
        """Delete user"""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False
            
            self.session.delete(user)
            self.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            self.session.rollback()
            return False

    def get_all_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all users with pagination"""
        try:
            return self.session.exec(select(User).offset(skip).limit(limit)).all()
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []

    def verify_user(self, user_id: str) -> bool:
        """Verify user account"""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False
            
            user.is_verified = True
            user.updated_at = datetime.utcnow()
            self.session.add(user)
            self.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error verifying user {user_id}: {e}")
            self.session.rollback()
            return False
