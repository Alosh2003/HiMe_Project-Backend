from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException, RequestValidationError
from app.core.logger import logger

# 1. Custom Exceptions
class CustomAPIException(Exception):
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST, errors: list = None):
        self.message = message
        self.status_code = status_code
        self.errors = errors or [message]

# 2. Handlers
async def custom_exception_handler(request: Request, exc: CustomAPIException):
    logger.error(f"Custom Exception: {exc.message} - Path: {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": exc.message, "errors": exc.errors}
    )

async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTP Exception {exc.status_code}: {exc.detail} - Path: {request.url.path}")
    detail_msg = exc.detail if isinstance(exc.detail, str) else "HTTP Error"
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": detail_msg, "errors": [detail_msg]}
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation Error - Path: {request.url.path}")
    errors = [f"{err['loc'][-1]}: {err['msg']}" for err in exc.errors()]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "Invalid request body or parameters",
            "errors": errors
        }
    )

async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.critical(f"Unhandled Server Error: {str(exc)} - Path: {request.url.path}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Internal server error occurred",
            "errors": ["An unexpected error happened on the server."]
        }
    )