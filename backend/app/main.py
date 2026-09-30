import logging
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.routes import auth, documents, health, mitigation, search
from app.services.auth_service import init_default_users

logger = logging.getLogger("cybershield")

# Ensure all database tables exist on startup
Base.metadata.create_all(bind=engine)
try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS content TEXT;"))
        conn.execute(text("ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedding TEXT;"))
except Exception as e:
    logger.info("Schema auto-update note: %s", e)

# Seed default admin and analyst accounts if they do not exist
try:
    with SessionLocal() as db_session:
        init_default_users(db_session)
except Exception as e:
    logger.warning("Default user seed note: %s", e)

app = FastAPI(
    title=settings.APP_NAME,
    description="CyberShield Cybersecurity Mitigation Retrieval Platform Backend",
    version="1.0.0",
    debug=settings.DEBUG,
)

# Centralized Error Handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status_code": exc.status_code,
            "error": exc.detail if isinstance(exc.detail, str) else "HTTP Error",
            "detail": exc.detail,
        },
        headers=getattr(exc, "headers", None) or {},
    )


def _clean_error_dict(err):
    clean = {}
    for k, v in err.items():
        if k == "ctx" and isinstance(v, dict):
            clean[k] = {ck: str(cv) for ck, cv in v.items()}
        elif isinstance(v, (str, int, float, bool, type(None))):
            clean[k] = v
        elif isinstance(v, (list, tuple)):
            clean[k] = list(v)
        else:
            clean[k] = str(v)
    return clean


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    formatted_errors = [_clean_error_dict(e) for e in exc.errors()]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status_code": 422,
            "error": "Unprocessable Entity",
            "detail": formatted_errors,
            "message": "Request validation failed. Please verify input parameters.",
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled server error: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status_code": 500,
            "error": "Internal Server Error",
            "detail": "An unexpected internal server error occurred.",
        },
    )


# Configure CORS Middleware
origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes (support both /api and /api/v1 prefixes)
app.include_router(health.router, prefix="/api/v1")
app.include_router(health.router, prefix="/api")

app.include_router(auth.router, prefix="/api")
app.include_router(auth.router, prefix="/api/v1")

app.include_router(documents.router, prefix="/api")
app.include_router(documents.router, prefix="/api/v1")

app.include_router(search.router, prefix="/api")
app.include_router(search.router, prefix="/api/v1")

app.include_router(mitigation.router, prefix="/api")
app.include_router(mitigation.router, prefix="/api/v1")


@app.get("/")
def root():
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "status": "online",
        "docs_url": "/docs",
    }
