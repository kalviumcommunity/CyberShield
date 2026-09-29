from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import Base, engine
from app.routes import documents, health, mitigation, search

# Ensure all database tables exist on startup
Base.metadata.create_all(bind=engine)
try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS content TEXT;"))
        conn.execute(text("ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedding TEXT;"))
except Exception as e:
    print(f"Schema auto-update note: {e}")

app = FastAPI(
    title=settings.APP_NAME,
    description="CyberShield Cybersecurity Mitigation Retrieval Platform Backend",
    version="1.0.0",
    debug=settings.DEBUG,
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
        "docs_url": "/docs"
    }
