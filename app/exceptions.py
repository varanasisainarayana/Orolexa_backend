from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from typing import Union

class APIException(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)

def create_error_response(error_message: str, status_code: int = 400) -> dict:
    """Create a standardized error response"""
    return {
        "success": False,
        "data": None,
        "error": error_message
    }

def create_success_response(data: dict) -> dict:
    """Create a standardized success response"""
    return {
        "success": True,
        "data": data,
        "error": None
    }

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Custom exception handler for HTTPException"""
    # Convert 403 from HTTPBearer to 401 for missing authentication
    if exc.status_code == 403 and "Not authenticated" in str(exc.detail):
        return JSONResponse(
            status_code=401,
            content=create_error_response("Authentication required", 401)
        )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(exc.detail, exc.status_code)
    )
