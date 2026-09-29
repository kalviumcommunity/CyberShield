from typing import List, Optional
from pydantic import BaseModel, Field


class SearchResultItem(BaseModel):
    """
    Schema for a single semantic search result chunk.
    Includes chunk ID, document ID, document title, chunk content,
    and similarity / relevance score.
    """
    chunk_id: int = Field(..., description="Unique ID of the document chunk")
    document_id: int = Field(..., description="ID of the parent document")
    document_title: str = Field(..., description="Title of the parent document")
    chunk_content: str = Field(..., description="Text content of the document chunk")
    similarity_score: float = Field(..., description="Semantic similarity score (cosine similarity, 0.0 to 1.0)")
    relevance_score: float = Field(..., description="Semantic relevance score (cosine similarity, 0.0 to 1.0)")
    content: Optional[str] = Field(None, description="Convenience alias for chunk_content")


class SearchResponse(BaseModel):
    """
    Optional wrapper response schema for search queries.
    """
    query: str = Field(..., description="The query string executed")
    top_k: int = Field(..., description="Requested top_k results count")
    total_results: int = Field(..., description="Number of results found")
    results: List[SearchResultItem] = Field(..., description="Ranked list of matching document chunks")


class SearchRebuildResponse(BaseModel):
    """
    Response schema for POST /api/search/rebuild
    """
    status: str = Field("success", description="Status of rebuild operation")
    indexed_chunks: int = Field(..., description="Number of document chunks indexed in FAISS")
    message: str = Field(..., description="Descriptive status message")
