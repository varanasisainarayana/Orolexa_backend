from sqlmodel import SQLModel, create_engine, Session
import os
import sqlite3
from .config import settings
from sqlalchemy.engine import URL

# Choose engine options based on database scheme
db_url = settings.DATABASE_URL
engine_kwargs = {}

if db_url.startswith("sqlite"):
    # SQLite specific connect args
    engine_kwargs.update({
        "connect_args": {"check_same_thread": False}
    })
else:
    # Better resiliency for managed Postgres
    engine_kwargs.update({
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": 5,
        "max_overflow": 10,
    })

engine = create_engine(db_url, echo=settings.DEBUG, **engine_kwargs)

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
        
        # Check if user table exists and migrate to new structure
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user'")
        if cursor.fetchone():
            # Check if we need to migrate from old user table to new users table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            if not cursor.fetchone():
                # Create new users table with UUID structure
                cursor.execute("""
                    CREATE TABLE users (
                        id VARCHAR(36) PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        phone VARCHAR(20) UNIQUE NOT NULL,
                        country_code VARCHAR(5) NOT NULL,
                        age INTEGER,
                        date_of_birth DATETIME,
                        profile_image_url VARCHAR(255),
                        email VARCHAR(100),
                        is_verified BOOLEAN DEFAULT FALSE,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes
                cursor.execute("CREATE INDEX idx_users_phone ON users(phone)")
                cursor.execute("CREATE INDEX idx_users_country_code ON users(country_code)")
                
                print("Created new users table with UUID structure")
        
        # Create OTP codes table if it doesn't exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='otp_codes'")
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE otp_codes (
                    id VARCHAR(36) PRIMARY KEY,
                    phone VARCHAR(20) NOT NULL,
                    otp VARCHAR(6) NOT NULL,
                    flow VARCHAR(10) NOT NULL,
                    is_used BOOLEAN DEFAULT FALSE,
                    expires_at DATETIME NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX idx_otp_codes_phone ON otp_codes(phone)")
            cursor.execute("CREATE INDEX idx_otp_codes_phone_flow ON otp_codes(phone, flow)")
            cursor.execute("CREATE INDEX idx_otp_codes_expires_at ON otp_codes(expires_at)")
            
            print("Created otp_codes table")
        
        # Create user sessions table if it doesn't exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_sessions'")
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE user_sessions (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL,
                    token VARCHAR(500) NOT NULL,
                    refresh_token VARCHAR(500) NOT NULL,
                    device_info TEXT,
                    ip_address VARCHAR(45),
                    expires_at DATETIME NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id)")
            cursor.execute("CREATE INDEX idx_user_sessions_token ON user_sessions(token)")
            cursor.execute("CREATE INDEX idx_user_sessions_refresh_token ON user_sessions(refresh_token)")
            
            print("Created user_sessions table")
        
        conn.commit()
        conn.close()
        print("Database migration completed successfully")
        
    except Exception as e:
        print(f"Error during database migration: {e}")

def get_session():
    with Session(engine) as session:
        yield session
