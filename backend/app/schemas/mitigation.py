from typing import List, Optional
from pydantic import BaseModel, Field


class MitigationResultItem(BaseModel):
    """
    Structured mitigation result retrieved from source cybersecurity documents.
    """
    document_id: int = Field(..., description="ID of the source document")
    document_title: str = Field(..., description="Title of the source document")
    document_type: str = Field(..., description="Type of document (e.g. incident_runbook, threat_intelligence, vulnerability_advisory)")
    chunk_id: int = Field(..., description="ID of the specific document chunk providing the mitigation")
    mitigation_text: str = Field(..., description="Verbatim mitigation steps extracted from the document chunk")
    relevance_score: float = Field(..., description="Semantic relevance score (cosine similarity, 0.0 to 1.0)")
    source_file: Optional[str] = Field(None, description="Original filename of the source document")


class MitigationSearchRequest(BaseModel):
    """
    Request schema for POST /api/mitigation/search
    """
    alert: str = Field(..., description="Active security alert description or observable behavior")
    top_k: Optional[int] = Field(5, description="Maximum number of relevant mitigation chunks to retrieve (1-100)")
    min_threshold: Optional[float] = Field(0.30, description="Minimum relevance score threshold for filtering results (0.0 to 1.0)")
    severity: Optional[str] = Field("medium", description="Alert severity level (low, medium, high, critical)")
    save_record: Optional[bool] = Field(True, description="Whether to persist the alert and mitigation audit record to PostgreSQL")


class MitigationSearchResponse(BaseModel):
    """
    Response schema for POST /api/mitigation/search
    """
    alert: str = Field(..., description="The queried active security alert")
    results: List[MitigationResultItem] = Field(..., description="List of relevant mitigations sorted by relevance score")
    total_results: Optional[int] = Field(None, description="Total number of relevant mitigations returned")
    alert_id: Optional[int] = Field(None, description="Database ID of the logged Alert record if stored")
