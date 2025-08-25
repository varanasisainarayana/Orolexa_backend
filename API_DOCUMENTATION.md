# 🦷 Orolexa API Documentation

## 📋 Overview

This is the complete API documentation for the Orolexa dental health app backend. The API provides comprehensive functionality for dental analysis, user management, doctor appointments, notifications, device management, and health analytics.

## 🚀 Base URL

```
http://localhost:8000
```

## 🔐 Authentication

All protected endpoints require JWT authentication via Bearer token in the Authorization header:

```
Authorization: Bearer <your_jwt_token>
```

---

## 📚 API Endpoints

### 🔐 Authentication Endpoints

#### 1. Send Registration OTP
```http
POST /auth/register/send-otp
Content-Type: multipart/form-data

mobile_number: "1234567890"
full_name: "John Doe"
profile_photo: [File] (optional)
```

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "OTP sent successfully",
    "status": "success"
  },
  "error": null
}
```

#### 2. Verify Registration OTP
```http
POST /auth/register/verify-otp
Content-Type: application/json

{
  "mobile_number": "1234567890",
  "otp_code": "123456"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  },
  "error": null
}
```

#### 3. Send Login OTP
```http
POST /auth/login/send-otp
Content-Type: application/json

{
  "mobile_number": "1234567890"
}
```

#### 4. Verify Login OTP
```http
POST /auth/login/verify-otp
Content-Type: application/json

{
  "mobile_number": "1234567890",
  "otp_code": "123456"
}
```

### 👤 User Profile Endpoints

#### 5. Get User Profile
```http
GET /profile
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 123,
    "full_name": "John Doe",
    "mobile_number": "1234567890",
    "profile_photo_url": "https://api.orolexa.com/uploads/profiles/user_123.jpg",
    "created_at": "2024-01-15T10:30:00Z"
  },
  "error": null
}
```

#### 6. Update User Profile
```http
PUT /profile
Authorization: Bearer <token>
Content-Type: multipart/form-data

full_name: "John Doe"
profile_photo: [File] (optional)
```

### 🦷 Dental Analysis Endpoints

#### 7. Upload Dental Images
```http
POST /upload-image
Authorization: Bearer <token>
Content-Type: multipart/form-data

file1: [required image file]
file2: [optional image file]
file3: [optional image file]
```

#### 8. Analyze Dental Images
```http
POST /analysis/analyze-images
Authorization: Bearer <token>
Content-Type: multipart/form-data

file1: [required image file]
file2: [optional image file]
file3: [optional image file]
doctor_name: "Dr. Smith" (optional)
```

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Analysis completed",
    "results": [
      {
        "filename": "dental_image.jpg",
        "saved_path": "/uploads/1234567890_dental_image.jpg",
        "image_url": "https://api.orolexa.com/uploads/1234567890_dental_image.jpg",
        "thumbnail_url": "https://api.orolexa.com/uploads/thumbnails/1234567890_dental_image.jpg",
        "analysis": "Comprehensive dental analysis text...",
        "history_id": 456,
        "doctor_name": "Dr. AI Assistant",
        "status": "completed",
        "created_at": "2024-01-15 10:30:00"
      }
    ]
  }
}
```

#### 9. Get Analysis History
```http
GET /analysis/history
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 456,
      "analysis": "Comprehensive dental analysis text...",
      "image_url": "https://api.orolexa.com/uploads/1234567890_dental_image.jpg",
      "thumbnail_url": "https://api.orolexa.com/uploads/thumbnails/1234567890_dental_image.jpg",
      "doctor_name": "Dr. AI Assistant",
      "status": "completed",
      "timestamp": "2024-01-15 10:30:00"
    }
  ]
}
```

### 👨‍⚕️ Doctor Management Endpoints

#### 10. Get Available Doctors
```http
GET /doctors?specialization=dentist&location=New York&rating=4.5&available=true
Authorization: Bearer <token>
```

**Response:**
```json
[
  {
    "id": 1,
    "name": "Dr. Sarah Johnson",
    "specialization": "General Dentistry",
    "experience": 8,
    "rating": 4.8,
    "location": "New York, NY",
    "latitude": 40.7128,
    "longitude": -74.0060,
    "available_slots": ["09:00", "10:00", "14:00"],
    "profile_image": "https://api.orolexa.com/uploads/doctors/dr_sarah.jpg",
    "is_available": true,
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

#### 11. Get Specific Doctor
```http
GET /doctors/{doctor_id}
Authorization: Bearer <token>
```

#### 12. Create Doctor (Admin)
```http
POST /doctors
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Dr. Sarah Johnson",
  "specialization": "General Dentistry",
  "experience": 8,
  "rating": 4.8,
  "location": "New York, NY",
  "latitude": 40.7128,
  "longitude": -74.0060,
  "available_slots": ["09:00", "10:00", "14:00"],
  "profile_image": "https://api.orolexa.com/uploads/doctors/dr_sarah.jpg",
  "is_available": true
}
```

### 📅 Appointment Endpoints

#### 13. Book Appointment
```http
POST /appointments
Authorization: Bearer <token>
Content-Type: application/json

{
  "doctor_id": 1,
  "patient_name": "John Doe",
  "patient_age": 30,
  "issue": "Regular dental checkup",
  "appointment_date": "2024-02-15",
  "appointment_time": "10:00"
}
```

**Response:**
```json
{
  "id": 789,
  "doctor_id": 1,
  "doctor_name": "Dr. Sarah Johnson",
  "patient_name": "John Doe",
  "patient_age": 30,
  "issue": "Regular dental checkup",
  "appointment_date": "2024-02-15",
  "appointment_time": "10:00",
  "status": "scheduled",
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### 14. Get User Appointments
```http
GET /appointments
Authorization: Bearer <token>
```

#### 15. Get Specific Appointment
```http
GET /appointments/{appointment_id}
Authorization: Bearer <token>
```

#### 16. Cancel Appointment
```http
PUT /appointments/{appointment_id}/cancel
Authorization: Bearer <token>
```

### 🔔 Notification Endpoints

#### 17. Get Notifications
```http
GET /notifications?type=appointment&read=false&limit=10&offset=0
Authorization: Bearer <token>
```

**Response:**
```json
[
  {
    "id": 123,
    "type": "appointment",
    "title": "Appointment Reminder",
    "message": "Your appointment with Dr. Sarah Johnson is tomorrow at 10:00 AM",
    "data": {
      "appointment_id": 789,
      "doctor_name": "Dr. Sarah Johnson"
    },
    "read": false,
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

#### 18. Mark Notification as Read
```http
PUT /notifications/{notification_id}/read
Authorization: Bearer <token>
```

#### 19. Mark All Notifications as Read
```http
PUT /notifications/read-all
Authorization: Bearer <token>
```

#### 20. Delete Notification
```http
DELETE /notifications/{notification_id}
Authorization: Bearer <token>
```

### 📱 Device Management Endpoints

#### 21. Get Device Status
```http
GET /device/status
Authorization: Bearer <token>
```

**Response:**
```json
{
  "connected": true,
  "device_id": "orolexa_device_001",
  "device_name": "Orolexa Smart Mirror",
  "ip_address": "192.168.1.100",
  "last_seen": "2024-01-15T10:30:00Z",
  "battery_level": 85,
  "firmware_version": "1.2.3"
}
```

#### 22. Connect Device
```http
POST /device/connect
Authorization: Bearer <token>
Content-Type: application/json

{
  "device_id": "orolexa_device_001",
  "device_name": "Orolexa Smart Mirror",
  "ip_address": "192.168.1.100"
}
```

#### 23. Disconnect Device
```http
POST /device/disconnect
Authorization: Bearer <token>
```

#### 24. Get Device Connections
```http
GET /device/connections
Authorization: Bearer <token>
```

### 🏥 Health & Analytics Endpoints

#### 25. Get Health Summary
```http
GET /health/summary
Authorization: Bearer <token>
```

**Response:**
```json
{
  "total_analyses": 5,
  "last_analysis_date": "2024-01-10",
  "health_score": 85,
  "recommendations": [
    "Schedule your next dental checkup",
    "Brush your teeth twice daily",
    "Floss regularly"
  ],
  "next_checkup_date": "2024-07-10"
}
```

#### 26. Get Analytics Data
```http
GET /health/analytics?period=month&type=analyses
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "period": "month",
    "type": "analyses",
    "data": [
      {
        "date": "2024-01-01",
        "value": 2
      },
      {
        "date": "2024-01-15",
        "value": 1
      }
    ],
    "summary": {
      "total": 3,
      "average": 1.5,
      "trend": "stable"
    }
  }
}
```

### ⚙️ Settings Endpoints

#### 27. Get App Settings
```http
GET /settings
Authorization: Bearer <token>
```

**Response:**
```json
{
  "notifications": {
    "push_enabled": true,
    "email_enabled": false,
    "sms_enabled": true
  },
  "privacy": {
    "data_sharing": true,
    "analytics": true
  },
  "preferences": {
    "language": "en",
    "theme": "light",
    "auto_sync": true
  }
}
```

#### 28. Update App Settings
```http
PUT /settings
Authorization: Bearer <token>
Content-Type: application/json

{
  "notifications": {
    "push_enabled": false
  },
  "preferences": {
    "theme": "dark"
  }
}
```

#### 29. Reset Settings
```http
POST /settings/reset
Authorization: Bearer <token>
```

### 🔧 Utility Endpoints

#### 30. Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "Dental AI API",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "environment": "local",
  "port": 8000,
  "database": {
    "ok": true,
    "error": null
  },
  "auth": {
    "secret_key_configured": true,
    "jwt_algorithm": "HS256",
    "token_expiry_minutes": 60
  }
}
```

---

## 🗄️ Database Schema

### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    full_name VARCHAR,
    mobile_number VARCHAR UNIQUE NOT NULL,
    profile_photo_url VARCHAR,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Analysis History Table
```sql
CREATE TABLE analysishistory (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    image_url VARCHAR NOT NULL,
    ai_report TEXT NOT NULL,
    doctor_name VARCHAR DEFAULT 'Dr. AI Assistant',
    status VARCHAR DEFAULT 'completed',
    thumbnail_url VARCHAR,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Doctors Table
```sql
CREATE TABLE doctor (
    id INTEGER PRIMARY KEY,
    name VARCHAR NOT NULL,
    specialization VARCHAR NOT NULL,
    experience INTEGER NOT NULL,
    rating FLOAT DEFAULT 0.0,
    location VARCHAR NOT NULL,
    latitude FLOAT,
    longitude FLOAT,
    available_slots VARCHAR DEFAULT '[]',
    profile_image VARCHAR,
    is_available BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Appointments Table
```sql
CREATE TABLE appointment (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    doctor_id INTEGER REFERENCES doctor(id),
    patient_name VARCHAR NOT NULL,
    patient_age INTEGER NOT NULL,
    issue TEXT NOT NULL,
    appointment_date DATE NOT NULL,
    appointment_time VARCHAR NOT NULL,
    status VARCHAR DEFAULT 'scheduled',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Notifications Table
```sql
CREATE TABLE notification (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    type VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    message TEXT NOT NULL,
    read BOOLEAN DEFAULT FALSE,
    data VARCHAR,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Device Connections Table
```sql
CREATE TABLE deviceconnection (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    device_id VARCHAR NOT NULL,
    device_name VARCHAR NOT NULL,
    ip_address VARCHAR,
    connected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    disconnected_at DATETIME,
    is_active BOOLEAN DEFAULT TRUE
);
```

### User Settings Table
```sql
CREATE TABLE usersettings (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) UNIQUE,
    notifications VARCHAR DEFAULT '{"push_enabled": true, "email_enabled": false, "sms_enabled": true}',
    privacy VARCHAR DEFAULT '{"data_sharing": true, "analytics": true}',
    preferences VARCHAR DEFAULT '{"language": "en", "theme": "light", "auto_sync": true}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🔒 Security Features

### JWT Authentication
- **Algorithm**: HS256
- **Expiry**: 60 minutes (configurable)
- **Token Structure**: Contains user ID and mobile number

### OTP Security
- **Length**: 6 digits
- **Expiry**: 10 minutes
- **Rate Limiting**: 3 attempts per 15 minutes
- **Delivery**: SMS via Twilio

### File Upload Security
- **Max Size**: 10MB per file
- **Allowed Types**: JPEG, PNG, WebP
- **Validation**: File type and size validation
- **Storage**: Secure local storage with unique filenames

### Rate Limiting
- **Requests per minute**: 60 (configurable)
- **Middleware**: Automatic rate limiting on all endpoints

---

## 🚀 Environment Variables

```env
# Database
DATABASE_URL=sqlite:///./app/orolexa.db

# JWT
JWT_SECRET_KEY=your_super_secret_jwt_key
JWT_ALGORITHM=HS256
JWT_EXPIRY=60

# Twilio (SMS)
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_VERIFY_SERVICE_SID=your_verify_service_sid

# AI Analysis
GEMINI_API_KEY=your_gemini_api_key

# App Configuration
APP_ENV=production
CORS_ORIGINS=https://orolexa.com,https://app.orolexa.com
BASE_URL=https://api.orolexa.com
```

---

## 📊 Response Format Standards

### Success Response
```json
{
  "success": true,
  "data": {
    // Response data here
  },
  "message": "Operation completed successfully"
}
```

### Error Response
```json
{
  "success": false,
  "error": "Error message here",
  "code": "ERROR_CODE",
  "details": {
    // Additional error details
  }
}
```

### Pagination Response
```json
{
  "success": true,
  "data": {
    "items": [],
    "pagination": {
      "page": 1,
      "limit": 10,
      "total": 100,
      "pages": 10
    }
  }
}
```

---

## 🎉 Conclusion

This API provides a complete backend solution for the Orolexa dental health app with:

✅ **Complete Authentication System** - OTP-based registration and login  
✅ **Dental Analysis** - AI-powered image analysis with Gemini  
✅ **Doctor Management** - CRUD operations for doctors  
✅ **Appointment Booking** - Full appointment lifecycle management  
✅ **Notifications** - Real-time notification system  
✅ **Device Management** - IoT device connection handling  
✅ **Health Analytics** - Comprehensive health insights  
✅ **User Settings** - Personalized app configuration  
✅ **Security** - JWT authentication, rate limiting, file validation  
✅ **Production Ready** - Docker support, health checks, logging  

The API is now fully implemented and ready for production deployment! 🚀
