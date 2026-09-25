from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from app.config import settings
from app.routes.health import router as health_router
from app.utils.error_handlers import (
    APIException,
    api_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    global_exception_handler,
)

# Initialize FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API service for CyberShield Threat Intelligence & Incident Mitigation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS Middleware for frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Error Handlers
app.add_exception_handler(APIException, api_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# Include Routers
app.include_router(health_router)

@app.get("/", include_in_schema=False)
def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "docs": "/docs",
        "health": "/api/health"
    }
