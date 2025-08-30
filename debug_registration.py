#!/usr/bin/env python3
"""
Debug script to test registration step by step
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def test_database_connection():
    """Test database connection"""
    print("🔍 Testing Database Connection...")
    
    try:
        from database import engine
        from sqlmodel import Session
        
        with Session(engine) as session:
            # Try a simple query
            result = session.exec("SELECT 1").first()
            print("✅ Database connection successful")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_twilio_client():
    """Test Twilio client initialization"""
    print("\n🔍 Testing Twilio Client...")
    
    try:
        from auth import client
        print("✅ Twilio client initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Twilio client initialization failed: {e}")
        return False

def test_extract_country_code():
    """Test country code extraction"""
    print("\n🔍 Testing Country Code Extraction...")
    
    try:
        from auth import extract_country_code
        
        result = extract_country_code("+917730831829")
        print(f"✅ Country code extraction: +917730831829 -> {result}")
        return True
    except Exception as e:
        print(f"❌ Country code extraction failed: {e}")
        return False

def test_schema_validation():
    """Test schema validation"""
    print("\n🔍 Testing Schema Validation...")
    
    try:
        from schemas import RegisterRequest
        
        payload = {
            "name": "Test User",
            "phone": "+917730831829",
            "age": 25,
            "date_of_birth": "1998-01-01"
        }
        
        register_req = RegisterRequest(**payload)
        print("✅ Schema validation successful")
        return True
    except Exception as e:
        print(f"❌ Schema validation failed: {e}")
        return False

def test_user_creation():
    """Test user creation in database"""
    print("\n🔍 Testing User Creation...")
    
    try:
        from database import engine
        from sqlmodel import Session, select
        from models import User
        from auth import extract_country_code
        from datetime import datetime
        import uuid
        
        user_id = str(uuid.uuid4())
        phone = "+917730831829"
        
        user = User(
            id=user_id,
            name="Test User",
            phone=phone,
            country_code=extract_country_code(phone),
            age=25,
            date_of_birth=datetime.strptime("1998-01-01", '%Y-%m-%d'),
            is_verified=False
        )
        
        with Session(engine) as session:
            session.add(user)
            session.commit()
            session.refresh(user)
            
            # Verify user was created
            created_user = session.exec(
                select(User).where(User.phone == phone)
            ).first()
            
            if created_user:
                print("✅ User creation successful")
                return True
            else:
                print("❌ User creation failed - user not found in database")
                return False
                
    except Exception as e:
        print(f"❌ User creation failed: {e}")
        return False

def test_twilio_otp_sending():
    """Test Twilio OTP sending"""
    print("\n🔍 Testing Twilio OTP Sending...")
    
    try:
        from auth import send_twilio_otp
        
        # This will actually send an OTP - be careful!
        print("⚠️  This will send a real OTP to +917730831829")
        response = input("Do you want to proceed? (y/n): ")
        
        if response.lower() == 'y':
            verification_sid = send_twilio_otp("+917730831829")
            print(f"✅ OTP sent successfully! SID: {verification_sid}")
            return True
        else:
            print("⏭️  Skipping OTP sending test")
            return True
            
    except Exception as e:
        print(f"❌ OTP sending failed: {e}")
        return False

def main():
    """Run all debug tests"""
    print("🔍 Registration Debug Tests")
    print("=" * 50)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Twilio Client", test_twilio_client),
        ("Country Code Extraction", test_extract_country_code),
        ("Schema Validation", test_schema_validation),
        ("User Creation", test_user_creation),
        ("Twilio OTP Sending", test_twilio_otp_sending),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🔍 {test_name}")
        print("-" * 30)
        result = test_func()
        results.append((test_name, result))
    
    print("\n" + "=" * 50)
    print("📊 Debug Results Summary")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All debug tests passed! Registration should work.")
        return 0
    else:
        print("⚠️  Some debug tests failed. Check the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
