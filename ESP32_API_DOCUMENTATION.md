# 🚀 ESP32-CAM API Documentation

## 📋 **Overview**

This document describes the complete ESP32-CAM API integration for your Orolexa Dental AI backend. The API provides endpoints for device management, image analysis, session handling, and real-time streaming.

---

## 🔐 **Authentication**

All endpoints require JWT Bearer token authentication:
```
Authorization: Bearer YOUR_JWT_TOKEN
```

---

## 🌐 **Base URL**

```
http://localhost:8000
```

---

## 📡 **API Endpoints**

### **1. Test ESP32-CAM Connection**

**Endpoint:** `POST /api/esp32/test-connection`

**Description:** Test connectivity to an ESP32-CAM device

**Request Schema:**
```json
{
  "ipAddress": "192.168.4.1",
  "port": 81,
  "streamPath": "/stream"
}
```

**Response Schema:**
```json
{
  "success": true,
  "message": "ESP32-CAM connection successful",
  "connectionDetails": {
    "isReachable": true,
    "responseTime": 45,
    "streamAvailable": true,
    "lastChecked": "2024-01-15T10:30:00.000Z"
  }
}
```

**Example Usage:**
```bash
curl -X POST "http://localhost:8000/api/esp32/test-connection" \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "ipAddress": "192.168.4.1",
       "port": 81,
       "streamPath": "/stream"
     }'
```

---

### **2. Analyze ESP32-CAM Images**

**Endpoint:** `POST /api/esp32/analyze-images`

**Description:** Analyze dental images from ESP32-CAM using Gemini AI

**Request Schema:**
```json
{
  "images": [
    "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ...",
    "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ..."
  ],
  "metadata": {
    "deviceId": "esp32_192.168.4.1",
    "timestamp": "2024-01-15T10:30:00.000Z",
    "ipAddress": "192.168.4.1",
    "imageCount": 2,
    "sessionId": "session_12345"
  },
  "analysisPreferences": {
    "analysisType": "dental",
    "priority": "normal",
    "includeConfidence": true
  }
}
```

**Response Schema:**
```json
{
  "status": "completed",
  "analysisId": "analysis_67890",
  "results": {
    "overallHealth": "good",
    "detectedIssues": [],
    "recommendations": [],
    "summary": "Overall dental health is good with minor issues...",
    "riskScore": 25
  },
  "processingTime": 2340,
  "timestamp": "2024-01-15T10:32:30.000Z",
  "nextSteps": [
    "Continue regular brushing and flossing",
    "Schedule dental appointment within 3 months",
    "Monitor gum health for any changes"
  ]
}
```

**Example Usage:**
```bash
curl -X POST "http://localhost:8000/api/esp32/analyze-images" \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "images": ["base64_image_data_here"],
       "metadata": {
         "deviceId": "esp32_192.168.4.1",
         "timestamp": "2024-01-15T10:30:00.000Z",
         "ipAddress": "192.168.4.1",
         "imageCount": 1
       }
     }'
```

---

### **3. Get ESP32-CAM Stream Status**

**Endpoint:** `GET /api/esp32/stream-status/{device_id}`

**Description:** Get real-time status of ESP32-CAM streaming

**Response Schema:**
```json
{
  "deviceId": "esp32_192.168.4.1",
  "isActive": true,
  "lastSeen": "2024-01-15T10:30:00.000Z",
  "streamQuality": "good",
  "connectionStats": {
    "uptime": 3600,
    "totalImages": 45,
    "lastImageTime": "2024-01-15T10:29:45.000Z",
    "averageResponseTime": 52
  },
  "deviceInfo": {
    "firmware": "ESP32-CAM v2.1.0",
    "model": "ESP32-CAM-MB",
    "resolution": "1600x1200",
    "frameRate": 30
  }
}
```

**Example Usage:**
```bash
curl -X GET "http://localhost:8000/api/esp32/stream-status/esp32_192.168.4.1" \
     -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

### **4. Create ESP32-CAM Session**

**Endpoint:** `POST /api/esp32/sessions`

**Description:** Create a new streaming session for ESP32-CAM

**Request Schema:**
```json
{
  "deviceId": "esp32_192.168.4.1",
  "ipAddress": "192.168.4.1",
  "port": 81,
  "streamPath": "/stream",
  "userId": "user_12345",
  "sessionType": "analysis"
}
```

**Response Schema:**
```json
{
  "sessionId": "session_67890",
  "deviceId": "esp32_192.168.4.1",
  "status": "active",
  "startTime": "2024-01-15T10:00:00.000Z",
  "totalImages": 0,
  "analysisCount": 0,
  "sessionUrl": "/api/esp32/sessions/session_67890"
}
```

**Example Usage:**
```bash
curl -X POST "http://localhost:8000/api/esp32/sessions" \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "deviceId": "esp32_192.168.4.1",
       "ipAddress": "192.168.4.1",
       "port": 81,
       "streamPath": "/stream",
       "sessionType": "analysis"
     }'
```

---

### **5. Upload ESP32-CAM Image**

**Endpoint:** `POST /api/esp32/upload-image`

**Description:** Upload captured images from ESP32-CAM

**Request Schema:**
```json
{
  "sessionId": "session_67890",
  "deviceId": "esp32_192.168.4.1",
  "image": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ...",
  "imageType": "jpeg",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "metadata": {
    "resolution": "1600x1200",
    "fileSize": 245760,
    "quality": 85,
    "captureMode": "auto"
  }
}
```

**Response Schema:**
```json
{
  "success": true,
  "imageId": "img_12345",
  "url": "/uploads/esp32_images/esp32_esp32_192.168.4.1_20240115_103000.jpeg",
  "thumbnailUrl": null,
  "message": "Image uploaded successfully"
}
```

**Example Usage:**
```bash
curl -X POST "http://localhost:8000/api/esp32/upload-image" \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "sessionId": "session_67890",
       "deviceId": "esp32_192.168.4.1",
       "image": "base64_image_data_here",
       "imageType": "jpeg",
       "timestamp": "2024-01-15T10:30:00.000Z"
     }'
```

---

### **6. Get ESP32-CAM Session**

**Endpoint:** `GET /api/esp32/sessions/{session_id}`

**Description:** Get detailed information about a specific session

**Response Schema:**
```json
{
  "sessionId": "session_67890",
  "deviceId": "esp32_192.168.4.1",
  "status": "active",
  "startTime": "2024-01-15T10:00:00.000Z",
  "totalImages": 12,
  "analysisCount": 2,
  "sessionUrl": "/api/esp32/sessions/session_67890",
  "images": [
    {
      "imageId": "img_12345",
      "sessionId": "session_67890",
      "deviceId": "esp32_192.168.4.1",
      "url": "/uploads/esp32_images/...",
      "imageType": "jpeg",
      "timestamp": "2024-01-15T10:30:00.000Z"
    }
  ],
  "imageCount": 1
}
```

**Example Usage:**
```bash
curl -X GET "http://localhost:8000/api/esp32/sessions/session_67890" \
     -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

### **7. Get All ESP32 Devices**

**Endpoint:** `GET /api/esp32/devices`

**Description:** Get list of all registered ESP32-CAM devices

**Response Schema:**
```json
{
  "devices": {
    "esp32_192.168.4.1": {
      "ip_address": "192.168.4.1",
      "port": 81,
      "stream_path": "/stream",
      "status": "online",
      "last_seen": "2024-01-15T10:30:00.000Z",
      "session_id": "session_67890"
    }
  },
  "total_devices": 1,
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

**Example Usage:**
```bash
curl -X GET "http://localhost:8000/api/esp32/devices" \
     -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

### **8. Get ESP32-CAM Analysis Results**

**Endpoint:** `GET /api/esp32/analysis/{analysis_id}`

**Description:** Get detailed analysis results for a specific analysis

**Response Schema:**
```json
{
  "status": "completed",
  "results": {
    "analysis": "Detailed AI analysis text...",
    "imageCount": 2,
    "analysisType": "dental"
  },
  "processingTime": 2340,
  "timestamp": "2024-01-15T10:32:30.000Z",
  "userId": 12345,
  "metadata": {
    "deviceId": "esp32_192.168.4.1",
    "timestamp": "2024-01-15T10:30:00.000Z"
  }
}
```

**Example Usage:**
```bash
curl -X GET "http://localhost:8000/api/esp32/analysis/analysis_67890" \
     -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## 🔧 **Integration with Your ESP32-CAM Code**

### **1. Update Your Arduino Code**

Add these API calls to your ESP32-CAM code:

```cpp
// Test connection
void testConnection() {
  HTTPClient http;
  http.begin("http://YOUR_SERVER_IP:8000/api/esp32/test-connection");
  http.addHeader("Authorization", "Bearer YOUR_JWT_TOKEN");
  http.addHeader("Content-Type", "application/json");
  
  String jsonData = "{\"ipAddress\":\"" + WiFi.localIP().toString() + "\",\"port\":81,\"streamPath\":\"/stream\"}";
  int httpCode = http.POST(jsonData);
  
  if (httpCode > 0) {
    String response = http.getString();
    Serial.println("Connection test: " + response);
  }
  http.end();
}

// Create session
void createSession() {
  HTTPClient http;
  http.begin("http://YOUR_SERVER_IP:8000/api/esp32/sessions");
  http.addHeader("Authorization", "Bearer YOUR_JWT_TOKEN");
  http.addHeader("Content-Type", "application/json");
  
  String jsonData = "{\"deviceId\":\"esp32_" + WiFi.localIP().toString().replace(".", "_") + "\",\"ipAddress\":\"" + WiFi.localIP().toString() + "\",\"port\":81,\"streamPath\":\"/stream\",\"sessionType\":\"analysis\"}";
  int httpCode = http.POST(jsonData);
  
  if (httpCode > 0) {
    String response = http.getString();
    Serial.println("Session created: " + response);
  }
  http.end();
}

// Upload captured image
void uploadImage(String base64Image, String sessionId) {
  HTTPClient http;
  http.begin("http://YOUR_SERVER_IP:8000/api/esp32/upload-image");
  http.addHeader("Authorization", "Bearer YOUR_JWT_TOKEN");
  http.addHeader("Content-Type", "application/json");
  
  String jsonData = "{\"sessionId\":\"" + sessionId + "\",\"deviceId\":\"esp32_" + WiFi.localIP().toString().replace(".", "_") + "\",\"image\":\"" + base64Image + "\",\"imageType\":\"jpeg\",\"timestamp\":\"" + getTimestamp() + "\"}";
  int httpCode = http.POST(jsonData);
  
  if (httpCode > 0) {
    String response = http.getString();
    Serial.println("Image uploaded: " + response);
  }
  http.end();
}
```

### **2. Complete Workflow**

1. **Start ESP32-CAM** → Connects to WiFi
2. **Test Connection** → Verify server connectivity
3. **Create Session** → Start new analysis session
4. **Capture Images** → Take photos during streaming
5. **Upload Images** → Send to server for analysis
6. **Get Analysis** → Retrieve AI analysis results
7. **Monitor Status** → Check device and stream health

---

## 📊 **Data Flow**

```
ESP32-CAM → WiFi → Your Server → Gemini AI → Analysis Results → Web Interface
```

---

## 🚀 **Testing the API**

### **1. Start Your Server**
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### **2. Test Endpoints**
```bash
# Test connection
curl -X POST "http://localhost:8000/api/esp32/test-connection" \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"ipAddress": "192.168.4.1", "port": 81, "streamPath": "/stream"}'

# Create session
curl -X POST "http://localhost:8000/api/esp32/sessions" \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"deviceId": "esp32_test", "ipAddress": "192.168.4.1", "port": 81, "streamPath": "/stream", "sessionType": "analysis"}'
```

### **3. View API Documentation**
Visit `http://localhost:8000/docs` for interactive API testing.

---

## 🎯 **Success Indicators**

- ✅ ESP32-CAM connects to WiFi
- ✅ Connection test passes
- ✅ Session created successfully
- ✅ Images uploaded without errors
- ✅ AI analysis completed
- ✅ Results retrieved successfully

---

## 🔍 **Troubleshooting**

### **Common Issues:**
1. **Authentication Failed** → Check JWT token validity
2. **Connection Timeout** → Verify server IP and port
3. **Image Upload Failed** → Check base64 encoding
4. **Analysis Failed** → Verify Gemini API key

### **Debug Steps:**
1. Check server logs for errors
2. Verify ESP32-CAM WiFi connection
3. Test API endpoints manually
4. Check image format and size

---

## 📝 **Notes**

- **Image Size Limit**: Maximum 10MB per image
- **Batch Processing**: Up to 10 images per analysis request
- **Session Management**: Automatic cleanup of old sessions
- **Real-time Updates**: Stream status updates every 5 seconds
- **AI Analysis**: Powered by Google Gemini for dental health assessment

Your backend is now fully equipped to handle ESP32-CAM integration with comprehensive API support! 🎉
