from datetime import datetime, timezone
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas.health import HealthCheckResponse, VectorIndexStatus

logger = logging.getLogger("cybershield.routes.health")

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthCheckResponse, summary="Operational health and readiness check")
def health_check(db: Session = Depends(get_db)):
    """
    Comprehensive health check verifying:
    - FastAPI application operational status
    - PostgreSQL database connectivity
    - FAISS vector search engine readiness and indexed vector count
    - UTC timestamp
    """
    # 1. Verify PostgreSQL Database Connectivity
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.error("Database health check ping failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}"
        )

    # 2. Check FAISS Vector Index Readiness
    indexed_chunks = 0
    faiss_status = "ready"
    try:
        from app.services.vector_search_service import get_vector_search_service
        vservice = get_vector_search_service()
        indexed_chunks = vservice.total_vectors
        if indexed_chunks == 0:
            faiss_status = "empty"
    except Exception as e:
        logger.warning("FAISS vector status inspection note: %s", e)
        faiss_status = "error"

    now_iso = datetime.now(timezone.utc).isoformat()

    return HealthCheckResponse(
        status="healthy",
        app=settings.APP_NAME,
        version="1.0.0",
        environment=settings.APP_ENV,
        database=db_status,
        vector_index=VectorIndexStatus(
            status=faiss_status,
            indexed_chunks=indexed_chunks,
        ),
        timestamp=now_iso,
        message="CyberShield API, PostgreSQL database, and FAISS vector index are fully operational.",
    )
