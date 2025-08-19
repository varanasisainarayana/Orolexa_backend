from sqlmodel import SQLModel, create_engine, Session
import os
import sqlite3
from .config import settings

engine = create_engine(settings.DATABASE_URL, echo=settings.DEBUG)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    # Only run the lightweight migration helper for SQLite
    if settings.DATABASE_URL.startswith("sqlite"):
        migrate_database()

def migrate_database():
    """Add new columns to existing tables if they don't exist (SQLite only)."""
    # Extract database path from DATABASE_URL
    if settings.DATABASE_URL.startswith('sqlite:///'):
        db_path = settings.DATABASE_URL.replace('sqlite:///', '')
    else:
        db_path = settings.DATABASE_URL.replace('sqlite://', '')
    
    if not os.path.exists(db_path):
        return  # Database doesn't exist, will be created by create_all()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if analysishistory table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='analysishistory'")
        if cursor.fetchone():
            # Add new columns to analysishistory table if they don't exist
            columns_to_add = [
                ('doctor_name', 'VARCHAR'),
                ('status', 'VARCHAR DEFAULT "completed"'),
                ('thumbnail_url', 'VARCHAR')
            ]
            
            for column_name, column_type in columns_to_add:
                try:
                    cursor.execute(f"ALTER TABLE analysishistory ADD COLUMN {column_name} {column_type}")
                    print(f"Added column {column_name} to analysishistory table")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        print(f"Column {column_name} already exists")
                    else:
                        print(f"Error adding column {column_name}: {e}")
        
        conn.commit()
        conn.close()
        print("Database migration completed successfully")
        
    except Exception as e:
        print(f"Error during database migration: {e}")

def get_session():
    with Session(engine) as session:
        yield session
