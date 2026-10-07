import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_admin
from app.models import User
from app.schemas.search import SearchRebuildResponse, SearchResultItem
from app.services.vector_search_service import get_vector_search_service

logger = logging.getLogger("cybershield.routes.search")

router = APIRouter(prefix="/search", tags=["Vector Search"])


@router.get("", response_model=List[SearchResultItem], summary="Semantic vector search for relevant document chunks")
@router.get("/", response_model=List[SearchResultItem], include_in_schema=False)
def search_documents(
    q: Optional[str] = Query(None, description="Security alert or mitigation query"),
    top_k: int = Query(5, description="Number of relevant document chunks to return (1-100)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Search document chunks semantically using FAISS vector similarity.

    When an analyst enters an active security alert or question,
    converts the query into a dense embedding and retrieves the most
    semantically relevant document chunks.

    Returns:
        List of matching document chunks with:
        - chunk ID
        - document ID
        - document title
        - chunk content
        - similarity/relevance score
    """
    # 1. Handle empty / whitespace queries
    if q is None or not q.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query 'q' cannot be empty.",
        )

    # 2. Validate top_k parameter
    if top_k is None or top_k < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="top_k must be an integer greater than or equal to 1.",
        )

    if top_k > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="top_k cannot exceed 100.",
        )

    # 3. Perform FAISS vector search
    try:
        service = get_vector_search_service()
        results = service.search(query=q, top_k=top_k, db=db)
        return results
    except Exception as e:
        logger.exception("Unexpected error during semantic vector search: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Semantic search failed: {str(e)}",
        )


@router.post("/rebuild", response_model=SearchRebuildResponse, summary="Rebuild FAISS index from document chunks")
def rebuild_search_index(
    auto_embed: bool = Query(False, description="Automatically embed any unembedded chunks before rebuilding"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Rebuilds the in-memory FAISS vector index from all document chunk embeddings stored in PostgreSQL.
    """
    try:
        service = get_vector_search_service()
        count = service.rebuild_index(db, auto_embed_unembedded=auto_embed)
        return SearchRebuildResponse(
            status="success",
            indexed_chunks=count,
            message=f"FAISS index rebuilt successfully with {count} document chunk(s).",
        )
    except Exception as e:
        logger.exception("Error rebuilding FAISS index: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rebuild FAISS index: {str(e)}",
        )
