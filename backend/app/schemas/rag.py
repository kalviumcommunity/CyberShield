from typing import List, Optional
from pydantic import BaseModel, Field

from app.schemas.mitigation import MitigationResultItem


class MitigationAnswerRequest(BaseModel):
    """
    Request schema for POST /api/mitigation/answer
    """
    alert: str = Field(..., description="Active security alert description")
    top_k: Optional[int] = Field(5, description="Maximum number of relevant chunks to retrieve (1-100)")
    min_threshold: Optional[float] = Field(0.35, description="Minimum relevance score threshold for filtering results (0.0 to 1.0)")
    severity: Optional[str] = Field("medium", description="Alert severity level")


class MitigationAnswerResponse(BaseModel):
    """
    Response schema for POST /api/mitigation/answer
    """
    alert: str = Field(..., description="The queried active security alert")
    answer: str = Field(..., description="Grounded AI mitigation answer synthesized strictly from retrieved context")
    sources: List[MitigationResultItem] = Field(..., description="List of source document chunks providing the mitigation evidence")
    results: Optional[List[MitigationResultItem]] = Field(None, description="Alias for sources to keep retrieval results accessible")
    alert_id: Optional[int] = Field(None, description="Database ID of the logged Alert record if stored")
