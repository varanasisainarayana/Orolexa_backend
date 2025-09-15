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
        
        # Check if it's PostgreSQL or SQLite
        is_postgres = "postgresql" in settings.DATABASE_URL.lower()
        
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                # Check if profile_image_id column exists
                if is_postgres:
                    result = conn.execute(text("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = 'users' 
                        AND column_name = 'profile_image_id'
                    """))
                else:
                    # SQLite - check if column exists
                    try:
                        result = conn.execute(text("""
                            PRAGMA table_info(users)
                        """))
                        columns = [row[1] for row in result.fetchall()]
                        result = type('obj', (object,), {'fetchone': lambda: None if 'profile_image_id' not in columns else ('profile_image_id',)})()
                    except:
                        result = type('obj', (object,), {'fetchone': lambda: None})()
                
                if not result.fetchone():
                    logger.info("Adding profile_image_id column to users table...")
                    if is_postgres:
                        conn.execute(text("""
                            ALTER TABLE users 
                            ADD COLUMN profile_image_id VARCHAR
                        """))
                    else:
                        conn.execute(text("""
                            ALTER TABLE users 
                            ADD COLUMN profile_image_id TEXT
                        """))
                    logger.info("profile_image_id column added successfully")
                else:
                    logger.info("profile_image_id column already exists")
                
                # Check if image_storage table exists
                if is_postgres:
                    result = conn.execute(text("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_name = 'image_storage'
                    """))
                else:
                    # SQLite
                    try:
                        result = conn.execute(text("""
                            SELECT name FROM sqlite_master 
                            WHERE type='table' AND name='image_storage'
                        """))
                    except:
                        result = type('obj', (object,), {'fetchone': lambda: None})()
                
                if not result.fetchone():
                    logger.info("Creating image_storage table...")
                    if is_postgres:
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
                    else:
                        conn.execute(text("""
                            CREATE TABLE image_storage (
                                id TEXT PRIMARY KEY,
                                user_id TEXT REFERENCES users(id),
                                filename TEXT NOT NULL,
                                content_type TEXT NOT NULL,
                                file_size INTEGER NOT NULL,
                                image_data BLOB NOT NULL,
                                image_type TEXT NOT NULL,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                width INTEGER,
                                height INTEGER,
                                thumbnail_id TEXT REFERENCES image_storage(id)
                            )
                        """))
                    logger.info("image_storage table created successfully")
                else:
                    logger.info("image_storage table already exists")
                
                # Add foreign key constraint for profile_image_id (PostgreSQL only)
                if is_postgres:
                    try:
                        conn.execute(text("""
                            ALTER TABLE users 
                            ADD CONSTRAINT fk_users_profile_image_id 
                            FOREIGN KEY (profile_image_id) REFERENCES image_storage(id)
                        """))
                        logger.info("Foreign key constraint added successfully")
                    except Exception as e:
                        if "already exists" in str(e) or "duplicate" in str(e).lower():
                            logger.info("Foreign key constraint already exists")
                        else:
                            logger.warning(f"Could not add foreign key constraint: {e}")
                
                # Commit transaction
                trans.commit()
                logger.info("Database migrations completed successfully")
                
            except Exception as e:
                # Rollback on error
                trans.rollback()
                logger.error(f"Migration failed: {e}")
                # Don't raise for SQLite compatibility issues
                if not is_postgres:
                    logger.warning("Migration skipped for SQLite - some features may not work")
                
    except Exception as e:
        logger.error(f"Error running migrations: {e}")
        # Don't raise for local development
        if "sqlite" in str(e).lower():
            logger.warning("Migration skipped for SQLite - continuing with limited functionality")

if __name__ == "__main__":
    run_migrations()
