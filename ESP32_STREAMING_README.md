# ESP32 Camera Streaming Integration

This document explains how to integrate ESP32 camera streaming with your dental AI backend.

## Overview

The streaming module provides real-time video streaming from ESP32 cameras to your frontend, with support for:
- **Real-time video streaming** via WebSocket and HTTP streaming
- **Snapshot capture** for analysis
- **Direct integration** with dental AI analysis
- **Authentication** and security

## ESP32 Camera Setup

### Required ESP32 Camera Endpoints

Your ESP32 camera should expose these endpoints:

1. **Root endpoint** (`/`) - For connection testing
2. **Snapshot endpoint** (`/capture`) - Returns JPEG image
3. **Stream endpoint** (`/stream`) - Returns MJPEG stream (optional)

### Example ESP32 Camera Code

```cpp
#include "esp_camera.h"
#include "esp_http_server.h"
#include "esp_timer.h"
#include "img_converters.h"
#include "Arduino.h"
#include "fb_gfx.h"
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"
#include "esp_http_server.h"

// Camera configuration
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    22
#define XCLK_GPIO_NUM     0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM       5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     4

void startCameraServer();

void setup() {
  Serial.begin(115200);
  Serial.setDebugOutput(true);
  Serial.println();

  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  
  // PSRAM IC required for UXGA resolution and high JPEG quality
  if(psramFound()){
    config.frame_size = FRAMESIZE_UXGA;
    config.jpeg_quality = 10;
    config.fb_count = 2;
  } else {
    config.frame_size = FRAMESIZE_SVGA;
    config.jpeg_quality = 12;
    config.fb_count = 1;
  }

  // Camera init
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return;
  }

  sensor_t * s = esp_camera_sensor_get();
  s->set_brightness(s, 0);     // -2 to 2
  s->set_contrast(s, 0);       // -2 to 2
  s->set_saturation(s, 0);     // -2 to 2
  s->set_special_effect(s, 0); // 0 to 6 (0 - No Effect, 1 - Negative, 2 - Grayscale, 3 - Red Tint, 4 - Green Tint, 5 - Blue Tint, 6 - Sepia)
  s->set_whitebal(s, 1);       // 0 = disable , 1 = enable
  s->set_awb_gain(s, 1);       // 0 = disable , 1 = enable
  s->set_wb_mode(s, 0);        // 0 to 4 - if awb_gain enabled (0 - Auto, 1 - Sunny, 2 - Cloudy, 3 - Office, 4 - Home)
  s->set_exposure_ctrl(s, 1);  // 0 = disable , 1 = enable
  s->set_aec2(s, 0);          // 0 = disable , 1 = enable
  s->set_gain_ctrl(s, 1);      // 0 = disable , 1 = enable
  s->set_agc_gain(s, 0);       // 0 to 30
  s->set_gainceiling(s, (gainceiling_t)0);  // 0 to 6
  s->set_bpc(s, 0);           // 0 = disable , 1 = enable
  s->set_wpc(s, 1);           // 0 = disable , 1 = enable
  s->set_raw_gma(s, 1);       // 0 = disable , 1 = enable
  s->set_lenc(s, 1);          // 0 = disable , 1 = enable
  s->set_hmirror(s, 0);       // 0 = disable , 1 = enable
  s->set_vflip(s, 0);         // 0 = disable , 1 = enable
  s->set_dcw(s, 1);           // 0 = disable , 1 = enable
  s->set_colorbar(s, 0);      // 0 = disable , 1 = enable

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi connected");

  startCameraServer();

  Serial.print("Camera Ready! Use 'http://");
  Serial.print(WiFi.localIP());
  Serial.println("' to connect");
}

void loop() {
  delay(1);
}

// Root endpoint
static esp_err_t root_handler(httpd_req_t *req){
    httpd_resp_set_type(req, "text/html");
    const char* response = "ESP32 Camera Ready";
    httpd_resp_send(req, response, strlen(response));
    return ESP_OK;
}

// Snapshot endpoint
static esp_err_t capture_handler(httpd_req_t *req){
    camera_fb_t * fb = NULL;
    esp_err_t res = ESP_OK;
    int64_t fr_start = 0;
    int64_t fr_end = 0;

    fb = esp_camera_fb_get();
    if (!fb) {
        Serial.println("Camera capture failed");
        httpd_resp_send_500(req);
        return ESP_FAIL;
    }

    httpd_resp_set_type(req, "image/jpeg");
    httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=capture.jpg");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

    res = httpd_resp_send(req, (const char *)fb->buf, fb->len);
    esp_camera_fb_return(fb);
    
    return res;
}

void startCameraServer(){
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();

    httpd_uri_t root_uri = {
        .uri       = "/",
        .method    = HTTP_GET,
        .handler   = root_handler,
        .user_ctx  = NULL
    };

    httpd_uri_t capture_uri = {
        .uri       = "/capture",
        .method    = HTTP_GET,
        .handler   = capture_handler,
        .user_ctx  = NULL
    };

    if (httpd_start(&camera_httpd, &config) == ESP_OK) {
        httpd_register_uri_handler(camera_httpd, &root_uri);
        httpd_register_uri_handler(camera_httpd, &capture_uri);
    }
}
```

## Backend API Endpoints

### 1. Setup Camera Connection
```http
POST /streaming/setup-camera
Content-Type: application/json
Authorization: Bearer <jwt_token>

{
    "ip_address": "192.168.1.100",
    "port": 80
}
```

**Response:**
```json
{
    "success": true,
    "message": "ESP32 camera connected successfully at http://192.168.1.100:80",
    "camera_url": "http://192.168.1.100:80",
    "stream_url": "http://192.168.1.100:80/stream",
    "snapshot_url": "http://192.168.1.100:80/capture"
}
```

### 2. Get Camera Status
```http
GET /streaming/camera-status
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
    "success": true,
    "is_connected": true,
    "camera_url": "http://192.168.1.100:80",
    "stream_url": "http://192.168.1.100:80/stream",
    "snapshot_url": "http://192.168.1.100:80/capture"
}
```

### 3. Get Snapshot
```http
GET /streaming/snapshot
Authorization: Bearer <jwt_token>
```

**Response:** JPEG image data

### 4. Stream Video (HTTP)
```http
GET /streaming/stream
Authorization: Bearer <jwt_token>
```

**Response:** Multipart MJPEG stream

### 5. WebSocket Stream
```javascript
const ws = new WebSocket('ws://your-api-url/streaming/ws-stream');
ws.onmessage = function(event) {
    if (event.data.startsWith('data:image/jpeg;base64,')) {
        // Update video element with base64 image
        document.getElementById('video').src = event.data;
    }
};
```

### 6. Analyze Stream Frame
```http
POST /streaming/analyze-stream
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
    "success": true,
    "message": "Frame captured successfully",
    "frame_size": [480, 640, 3],
    "image_bytes_length": 45678,
    "camera_url": "http://192.168.1.100:80"
}
```

### 7. Disconnect Camera
```http
DELETE /streaming/disconnect-camera
Authorization: Bearer <jwt_token>
```

## Frontend Integration

### Basic HTML Video Element
```html
<img id="videoStream" src="" alt="Video Stream" style="display: none;">
```

### JavaScript Integration
```javascript
// Setup camera
async function setupCamera(ipAddress, port = 80) {
    const response = await fetch('/streaming/setup-camera', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
            ip_address: ipAddress,
            port: port
        })
    });
    return response.json();
}

// Start HTTP stream
function startStream() {
    const videoElement = document.getElementById('videoStream');
    videoElement.src = '/streaming/stream';
    videoElement.style.display = 'block';
}

// Start WebSocket stream
function startWebSocketStream() {
    const ws = new WebSocket('ws://your-api-url/streaming/ws-stream');
    
    ws.onmessage = function(event) {
        if (event.data.startsWith('data:image/jpeg;base64,')) {
            const videoElement = document.getElementById('videoStream');
            videoElement.src = event.data;
            videoElement.style.display = 'block';
        }
    };
}

// Get snapshot
async function getSnapshot() {
    const response = await fetch('/streaming/snapshot', {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    
    if (response.ok) {
        const blob = await response.blob();
        const imageUrl = URL.createObjectURL(blob);
        document.getElementById('videoStream').src = imageUrl;
    }
}

// Analyze frame
async function analyzeFrame() {
    const response = await fetch('/streaming/analyze-stream', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    
    const result = await response.json();
    console.log('Analysis result:', result);
}
```

## Integration with Dental AI Analysis

The streaming module can be integrated with your existing dental AI analysis:

```python
# In your analysis.py, add this function
async def analyze_esp32_frame(frame_bytes: bytes, current_user: str):
    """
    Analyze a frame captured from ESP32 camera
    """
    # Convert frame bytes to the format expected by your analysis
    # This would integrate with your existing quick-assessment or detailed-analysis endpoints
    
    # Example integration with quick assessment
    # You would need to modify the existing endpoints to accept bytes instead of files
    pass
```

## Security Considerations

1. **Authentication**: All endpoints require JWT authentication
2. **Network Security**: Ensure ESP32 camera is on a secure network
3. **CORS**: Configure CORS settings for your frontend domain
4. **Rate Limiting**: Consider implementing rate limiting for streaming endpoints

## Performance Optimization

1. **Frame Rate**: Adjust frame rate based on network capacity
2. **Image Quality**: Optimize JPEG quality for balance between quality and bandwidth
3. **Caching**: Implement appropriate caching headers
4. **Compression**: Use GZIP compression for HTTP responses

## Troubleshooting

### Common Issues

1. **Connection Failed**
   - Check ESP32 IP address and port
   - Ensure ESP32 is on the same network
   - Verify ESP32 camera endpoints are working

2. **Stream Not Loading**
   - Check CORS settings
   - Verify authentication token
   - Check network connectivity

3. **Poor Performance**
   - Reduce frame rate
   - Lower image quality
   - Check network bandwidth

### Debug Logs

Enable debug logging in your FastAPI application:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Testing

Use the provided `streaming_test.html` file to test the streaming functionality:

1. Update the `API_BASE` and `TOKEN` variables in the HTML file
2. Open the file in a web browser
3. Enter your ESP32 camera IP address
4. Test different streaming modes

## Next Steps

1. **Real-time Analysis**: Integrate streaming with real-time dental analysis
2. **Recording**: Add video recording functionality
3. **Multiple Cameras**: Support multiple ESP32 cameras
4. **Mobile App**: Create mobile app integration
5. **Cloud Storage**: Add cloud storage for recorded videos
