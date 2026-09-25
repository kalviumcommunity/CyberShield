from pydantic import BaseModel, Field

class HealthCheckResponse(BaseModel):
    """
    Response schema for the API health check endpoint.
    """
    status: str = Field(..., description="Current operational status of the service")
    app_name: str = Field(..., description="Name of the backend service")
    environment: str = Field(..., description="Environment mode")
    timestamp: str = Field(..., description="Current UTC timestamp")
