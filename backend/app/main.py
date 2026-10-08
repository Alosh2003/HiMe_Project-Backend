from fastapi import FastAPI
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logger import logger
from app.core.exceptions import (
    CustomAPIException,
    custom_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    unhandled_exception_handler,
)
from app.api.auth import router as auth_router
from app.api.seekers import router as seekers_router
from app.api.companies import router as companies_router
from app.api.applications import router as applications_router
from app.api.ai_matching import router as ai_matching_router
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(CustomAPIException, custom_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

@app.on_event("startup")
async def startup_event():
    logger.info("Application starting up successfully...")

# 4. تضمين الـ Routers
app.include_router(auth_router)
app.include_router(seekers_router)
app.include_router(companies_router)
app.include_router(applications_router)
app.include_router(ai_matching_router)

@app.get("/")
def read_root():
    return {"success": True, "message": "HiMe Platform API is running nooowwww!", "data": None}