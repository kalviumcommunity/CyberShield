from typing import Any, Dict
from pydantic import BaseModel, Field


class VectorIndexStatus(BaseModel):
    """
    Status of the in-memory FAISS vector index.
    """
    status: str = Field(..., description="Operational status of FAISS index ('ready', 'empty', or 'error')")
    indexed_chunks: int = Field(..., description="Total number of document chunks indexed in FAISS")


class HealthCheckResponse(BaseModel):
    """
    Response schema for the API health check endpoint.
    """
    status: str = Field(..., description="Current operational status of the service ('healthy' or 'unhealthy')")
    app: str = Field(..., description="Application name")
    version: str = Field("1.0.0", description="API version")
    environment: str = Field(..., description="Deployment environment mode")
    database: str = Field(..., description="Database connectivity status ('connected' or 'disconnected')")
    vector_index: VectorIndexStatus = Field(..., description="FAISS vector search engine status")
    timestamp: str = Field(..., description="Current UTC ISO 8601 timestamp")
    message: str = Field(..., description="Descriptive status message")
