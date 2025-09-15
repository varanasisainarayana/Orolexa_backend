# Production Deployment Guide

## 🚀 Production-Ready OTP System

This guide provides comprehensive instructions for deploying the OTP authentication system to production with enhanced security, monitoring, and reliability.

## 📋 Pre-Deployment Checklist

### ✅ Security Requirements
- [ ] Strong JWT secret key configured
- [ ] Twilio credentials secured
- [ ] Database credentials encrypted
- [ ] HTTPS/SSL certificates installed
- [ ] Firewall rules configured
- [ ] Rate limiting enabled
- [ ] Audit logging enabled
- [ ] Security headers configured

### ✅ Infrastructure Requirements
- [ ] Production database (PostgreSQL/MySQL)
- [ ] Redis for caching and rate limiting
- [ ] Load balancer configured
- [ ] CDN for static assets
- [ ] Backup system configured
- [ ] Monitoring and alerting setup
- [ ] Log aggregation system

### ✅ Environment Configuration
- [ ] Environment variables secured
- [ ] Production settings configured
- [ ] Logging levels set appropriately
- [ ] CORS origins restricted
- [ ] Database connection pooling

## 🔧 Production Configuration

### 1. Environment Variables

Create a production `.env` file:

```bash
# Application Settings
APP_NAME=Orolexa Production
APP_VERSION=1.0.0
DEBUG=false
DOCS_ENABLED=false

# Server Settings
HOST=0.0.0.0
PORT=8000
WORKERS=4

# Database Settings (Production)
DATABASE_URL=postgresql://user:password@host:5432/orolexa_prod

# Security Settings
JWT_SECRET_KEY=your-super-secure-jwt-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Twilio Settings
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_VERIFY_SERVICE_SID=your-twilio-verify-service-sid

# CORS Settings (Production)
CORS_ORIGINS=https://app.orolexa.com,https://orolexa.com

# Redis Settings
REDIS_URL=redis://localhost:6379/0

# Monitoring Settings
SENTRY_DSN=your-sentry-dsn
PROMETHEUS_ENABLED=true

# Backup Settings
BACKUP_ENABLED=true
BACKUP_S3_BUCKET=orolexa-backups
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-1
```

### 2. Production Settings

Update `app/config.py` to use production settings:

```python
# Production-specific settings
PRODUCTION_MODE = True
SECURITY_LEVEL = "high"
ENABLE_AUDIT_LOGGING = True
ENABLE_FRAUD_DETECTION = True
RATE_LIMIT_ENABLED = True
```

### 3. Database Configuration

For production, use PostgreSQL with connection pooling:

```python
# Database connection with pooling
DATABASE_URL = "postgresql://user:password@host:5432/orolexa_prod"
DB_CONNECTION_POOL_SIZE = 20
DB_MAX_OVERFLOW = 30
DB_POOL_TIMEOUT = 30
```

## 🐳 Docker Production Setup

### 1. Production Dockerfile

```dockerfile
# Production Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV TZ=UTC

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Create log directory
RUN mkdir -p /var/log/orolexa

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/auth/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### 2. Docker Compose for Production

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/orolexa_prod
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - ./logs:/var/log/orolexa
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/auth/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=orolexa_prod
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

## 🔒 Security Hardening

### 1. Security Headers

Configure Nginx with security headers:

```nginx
# nginx.conf
server {
    listen 443 ssl http2;
    server_name api.orolexa.com;

    # SSL Configuration
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;

    # Security Headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
    add_header Referrer-Policy "strict-origin-when-cross-origin";
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'";

    location / {
        proxy_pass http://app:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 2. Rate Limiting

Implement rate limiting at the Nginx level:

```nginx
# Rate limiting configuration
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=otp:10m rate=1r/m;

location /api/auth/login {
    limit_req zone=otp burst=3 nodelay;
    proxy_pass http://app:8000;
}

location /api/auth/register {
    limit_req zone=otp burst=2 nodelay;
    proxy_pass http://app:8000;
}

location /api/auth/verify-otp {
    limit_req zone=otp burst=5 nodelay;
    proxy_pass http://app:8000;
}
```

### 3. Database Security

```sql
-- Create production database user with limited privileges
CREATE USER orolexa_user WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE orolexa_prod TO orolexa_user;
GRANT USAGE ON SCHEMA public TO orolexa_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO orolexa_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO orolexa_user;
```

## 📊 Monitoring and Alerting

### 1. Health Checks

The system includes built-in health check endpoints:

```bash
# Health check
curl https://api.orolexa.com/api/auth/health

# Metrics
curl https://api.orolexa.com/api/auth/metrics
```

### 2. Prometheus Metrics

Add Prometheus monitoring:

```python
# Add to requirements.txt
prometheus-client>=0.19.0

# Add to main.py
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# Metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency')

@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    REQUEST_LATENCY.observe(duration)
    return response

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

### 3. Logging Configuration

Configure structured logging:

```python
# logging_config.py
import logging.config
from app.production_config import LOGGING_CONFIG

logging.config.dictConfig(LOGGING_CONFIG)
```

### 4. Sentry Integration

Add error tracking:

```python
# Add to requirements.txt
sentry-sdk[fastapi]>=1.38.0

# Add to main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    integrations=[FastApiIntegration()],
    traces_sample_rate=0.1,
    environment="production"
)
```

## 🔄 Backup and Recovery

### 1. Database Backup

```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="orolexa_backup_$DATE.sql"

# Create backup
pg_dump $DATABASE_URL > /backups/$BACKUP_FILE

# Compress backup
gzip /backups/$BACKUP_FILE

# Upload to S3
aws s3 cp /backups/$BACKUP_FILE.gz s3://orolexa-backups/

# Clean old backups (keep 30 days)
find /backups -name "*.sql.gz" -mtime +30 -delete
```

### 2. Automated Backup Cron Job

```bash
# Add to crontab
0 2 * * * /app/backup.sh
```

## 🚨 Incident Response

### 1. Monitoring Alerts

Set up alerts for:
- High error rates (>5%)
- High response times (>2s)
- Service downtime
- Database connection issues
- Twilio API failures

### 2. Emergency Procedures

```bash
# Emergency rollback
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d app:previous-version

# Database recovery
pg_restore $DATABASE_URL < /backups/latest_backup.sql

# Service restart
docker-compose -f docker-compose.prod.yml restart app
```

## 📈 Performance Optimization

### 1. Database Optimization

```sql
-- Create indexes for better performance
CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_otp_codes_phone_flow ON otp_codes(phone, flow);
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_expires_at ON user_sessions(expires_at);
```

### 2. Caching Strategy

```python
# Redis caching for frequently accessed data
import redis

redis_client = redis.Redis.from_url(settings.REDIS_URL)

def get_user_cached(user_id: str):
    cache_key = f"user:{user_id}"
    cached_user = redis_client.get(cache_key)
    
    if cached_user:
        return json.loads(cached_user)
    
    # Fetch from database
    user = get_user_from_db(user_id)
    
    # Cache for 5 minutes
    redis_client.setex(cache_key, 300, json.dumps(user.dict()))
    return user
```

### 3. Connection Pooling

```python
# Database connection pooling
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_timeout=30,
    pool_recycle=3600
)
```

## 🔍 Testing in Production

### 1. Load Testing

```bash
# Install k6 for load testing
curl -L https://github.com/grafana/k6/releases/download/v0.45.0/k6-v0.45.0-linux-amd64.tar.gz | tar xz

# Load test script
cat > load-test.js << EOF
import http from 'k6/http';
import { check } from 'k6';

export const options = {
  stages: [
    { duration: '2m', target: 100 },
    { duration: '5m', target: 100 },
    { duration: '2m', target: 0 },
  ],
};

export default function () {
  const payload = JSON.stringify({
    phone: '+1234567890',
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  const response = http.post('https://api.orolexa.com/api/auth/login', payload, params);

  check(response, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });
}
EOF

# Run load test
k6 run load-test.js
```

### 2. Security Testing

```bash
# OWASP ZAP security scan
docker run -v $(pwd):/zap/wrk/:rw -t owasp/zap2docker-stable zap-baseline.py \
  -t https://api.orolexa.com \
  -J zap-report.json
```

## 📋 Database Migrations (Alembic)

Apply database migrations using Alembic either during deployment or on startup:

```bash
# During deployment (recommended)
alembic upgrade head

# Or enable on startup
RUN_ALEMBIC_ON_STARTUP=true uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Ensure your `DATABASE_URL` is configured correctly in the environment.

## 📋 Deployment Checklist

### Pre-Deployment
- [ ] All tests passing
- [ ] Security scan completed
- [ ] Load testing performed
- [ ] Backup system tested
- [ ] Monitoring configured
- [ ] SSL certificates installed
- [ ] Environment variables set
- [ ] Database migrations applied (Alembic `upgrade head`)

### Deployment
- [ ] Deploy to staging environment
- [ ] Run smoke tests
- [ ] Deploy to production
- [ ] Verify health checks
- [ ] Monitor error rates
- [ ] Check performance metrics
- [ ] Validate OTP functionality

### Post-Deployment
- [ ] Monitor logs for errors
- [ ] Check system metrics
- [ ] Verify backup jobs
- [ ] Test alerting system
- [ ] Document any issues
- [ ] Update runbooks

## 🎯 Production Best Practices

1. **Security First**: Always prioritize security over convenience
2. **Monitor Everything**: Set up comprehensive monitoring and alerting
3. **Automate Everything**: Use CI/CD pipelines for deployments
4. **Backup Regularly**: Implement automated backup and recovery procedures
5. **Test in Production**: Use feature flags and gradual rollouts
6. **Document Everything**: Maintain up-to-date documentation
7. **Plan for Failure**: Have incident response procedures ready
8. **Scale Horizontally**: Design for horizontal scaling from the start

## 📞 Support and Maintenance

- **24/7 Monitoring**: Set up round-the-clock monitoring
- **Incident Response**: Have a clear escalation procedure
- **Regular Updates**: Keep dependencies and security patches updated
- **Performance Tuning**: Regularly review and optimize performance
- **Capacity Planning**: Monitor usage trends and plan for growth

The OTP system is now production-ready with enterprise-grade security, monitoring, and reliability features!
