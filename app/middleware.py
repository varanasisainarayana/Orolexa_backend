import time
import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import hashlib
from collections import defaultdict
import asyncio
from .config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format=settings.LOG_FORMAT
)
logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.requests = defaultdict(list)
        self.rate_limit = settings.RATE_LIMIT_PER_MINUTE
        
    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Clean old requests (older than 1 minute)
        current_time = time.time()
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if current_time - req_time < 60
        ]
        
        # Check rate limit
        if len(self.requests[client_ip]) >= self.rate_limit:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please try again later."}
            )
        
        # Add current request
        self.requests[client_ip].append(current_time)
        
        # Continue with request
        response = await call_next(request)
        return response

class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Add security headers
        response = await call_next(request)
        
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log request (guard against missing client info)
        client_host = request.client.host if request.client else "unknown"
        logger.info(f"Request: {request.method} {request.url.path} from {client_host}")
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log response
        logger.info(f"Response: {response.status_code} in {duration:.3f}s")
        
        return response

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(f"Unhandled error: {str(e)}", exc_info=True)
            
            if settings.DEBUG:
                return JSONResponse(
                    status_code=500,
                    content={"detail": f"Internal server error: {str(e)}"}
                )
            else:
                return JSONResponse(
                    status_code=500,
                    content={"detail": "Internal server error"}
                )

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Enforce a hard cap on request size using Content-Length when available
        try:
            content_length = request.headers.get("content-length")
            if content_length is not None:
                try:
                    size = int(content_length)
                    if size > settings.MAX_FILE_SIZE:
                        return JSONResponse(
                            status_code=413,
                            content={"detail": "Request entity too large"}
                        )
                except ValueError:
                    # Malformed header; proceed but still guarded by downstream file checks
                    pass
            return await call_next(request)
        except Exception as e:
            logger.error(f"RequestSizeLimitMiddleware error: {e}")
            return JSONResponse(status_code=500, content={"detail": "Internal server error"})