from datetime import datetime, timezone
from fastapi import APIRouter, status
from app.config import settings
from app.schemas.health import HealthCheckResponse

router = APIRouter(prefix="/api", tags=["Health"])

@router.get(
    "/health",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="API Health Check",
    description="Returns operational health status and system metadata."
)
def get_health():
    return HealthCheckResponse(
        status="healthy",
        app_name=settings.APP_NAME,
        environment=settings.APP_ENV,
        timestamp=datetime.now(timezone.utc).isoformat()
    )
