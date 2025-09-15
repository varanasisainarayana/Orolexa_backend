#!/usr/bin/env python3
"""
Manual database migration script
Run this to add the missing columns to your production database
"""
import os
import sys
from sqlalchemy import create_engine, text

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import settings

def migrate_database():
    """
    Add missing columns to the database
    """
    try:
        print("Connecting to database...")
        engine = create_engine(settings.DATABASE_URL)
        
        # Check if it's PostgreSQL or SQLite
        is_postgres = "postgresql" in settings.DATABASE_URL.lower()
        
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                print("Checking database schema...")
                
                # Check if profile_image_id column exists
                if is_postgres:
                    result = conn.execute(text("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = 'users' 
                        AND column_name = 'profile_image_id'
                    """))
                else:
                    # SQLite
                    result = conn.execute(text("""
                        PRAGMA table_info(users)
                    """))
                    columns = [row[1] for row in result.fetchall()]
                    result = type('obj', (object,), {'fetchone': lambda: None if 'profile_image_id' not in columns else ('profile_image_id',)})()
                
                if not result.fetchone():
                    print("Adding profile_image_id column to users table...")
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
                    print("✓ profile_image_id column added successfully")
                else:
                    print("✓ profile_image_id column already exists")
                
                # Check if image_storage table exists
                if is_postgres:
                    result = conn.execute(text("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_name = 'image_storage'
                    """))
                else:
                    # SQLite
                    result = conn.execute(text("""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name='image_storage'
                    """))
                
                if not result.fetchone():
                    print("Creating image_storage table...")
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
                    print("✓ image_storage table created successfully")
                else:
                    print("✓ image_storage table already exists")
                
                # Add foreign key constraint for profile_image_id (PostgreSQL only)
                if is_postgres:
                    print("Adding foreign key constraint for profile_image_id...")
                    try:
                        conn.execute(text("""
                            ALTER TABLE users 
                            ADD CONSTRAINT fk_users_profile_image_id 
                            FOREIGN KEY (profile_image_id) REFERENCES image_storage(id)
                        """))
                        print("✓ Foreign key constraint added successfully")
                    except Exception as e:
                        if "already exists" in str(e) or "duplicate" in str(e).lower():
                            print("✓ Foreign key constraint already exists")
                        else:
                            print(f"⚠ Warning: Could not add foreign key constraint: {e}")
                
                # Commit transaction
                trans.commit()
                print("\n🎉 Database migration completed successfully!")
                
            except Exception as e:
                # Rollback on error
                trans.rollback()
                print(f"❌ Migration failed: {e}")
                raise
                
    except Exception as e:
        print(f"❌ Error running migration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("🔄 Starting database migration...")
    migrate_database()
    print("✅ Migration completed!")
