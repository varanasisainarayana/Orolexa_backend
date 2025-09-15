# app/migrations.py
"""
Database migration script to add new columns for image storage
"""
import os
from sqlalchemy import create_engine, text
from .config import settings
import logging

logger = logging.getLogger(__name__)

def run_migrations():
    """
    Run database migrations to add new columns
    """
    try:
        # Create engine
        engine = create_engine(settings.DATABASE_URL)
        
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                # Check if profile_image_id column exists
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'users' 
                    AND column_name = 'profile_image_id'
                """))
                
                if not result.fetchone():
                    logger.info("Adding profile_image_id column to users table...")
                    conn.execute(text("""
                        ALTER TABLE users 
                        ADD COLUMN profile_image_id VARCHAR REFERENCES image_storage(id)
                    """))
                    logger.info("profile_image_id column added successfully")
                else:
                    logger.info("profile_image_id column already exists")
                
                # Check if image_storage table exists
                result = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_name = 'image_storage'
                """))
                
                if not result.fetchone():
                    logger.info("Creating image_storage table...")
                    conn.execute(text("""
                        CREATE TABLE image_storage (
                            id VARCHAR PRIMARY KEY,
                            user_id VARCHAR REFERENCES users(id),
                            filename VARCHAR(255) NOT NULL,
                            content_type VARCHAR(100) NOT NULL,
                            file_size INTEGER NOT NULL,
                            image_data BYTEA NOT NULL,
                            image_type VARCHAR(50) NOT NULL,
                            created_at TIMESTAMP DEFAULT NOW(),
                            width INTEGER,
                            height INTEGER,
                            thumbnail_id VARCHAR REFERENCES image_storage(id)
                        )
                    """))
                    logger.info("image_storage table created successfully")
                else:
                    logger.info("image_storage table already exists")
                
                # Commit transaction
                trans.commit()
                logger.info("Database migrations completed successfully")
                
            except Exception as e:
                # Rollback on error
                trans.rollback()
                logger.error(f"Migration failed: {e}")
                raise
                
    except Exception as e:
        logger.error(f"Error running migrations: {e}")
        raise

if __name__ == "__main__":
    run_migrations()
