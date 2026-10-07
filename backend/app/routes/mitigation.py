import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.mitigation import MitigationSearchRequest, MitigationSearchResponse
from app.schemas.rag import MitigationAnswerRequest, MitigationAnswerResponse
from app.services.mitigation_service import get_mitigation_service
from app.services.rag_service import get_rag_service

logger = logging.getLogger("cybershield.routes.mitigation")

router = APIRouter(prefix="/mitigation", tags=["Mitigation Retrieval"])


@router.post("/search", response_model=MitigationSearchResponse, summary="Retrieve cybersecurity mitigations for an active security alert")
def retrieve_mitigations(
    request: MitigationSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Search and retrieve verbatim cybersecurity mitigation steps for an active security alert.

    - Uses FAISS semantic search to find semantically relevant chunks across:
      - Incident runbooks
      - Threat intelligence reports
      - Vulnerability advisories
    - Filters results by relevance threshold and sorts in descending order.
    - Always preserves the original source document metadata (title, type, ID).
    - Logs the alert and matching mitigation results in PostgreSQL for incident auditing.
    """
    # 1. Validate alert text
    if not request.alert or not request.alert.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Alert text cannot be empty.",
        )

    # 2. Validate top_k parameter
    top_k = request.top_k if request.top_k is not None else 5
    if top_k < 1 or top_k > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="top_k must be an integer between 1 and 100.",
        )

    # 3. Validate min_threshold parameter
    min_threshold = request.min_threshold if request.min_threshold is not None else 0.30
    if min_threshold < 0.0 or min_threshold > 1.0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="min_threshold must be a float between 0.0 and 1.0.",
        )

    # 4. Execute mitigation search
    try:
        service = get_mitigation_service()
        response_data = service.search_mitigations(
            alert=request.alert,
            top_k=top_k,
            min_threshold=min_threshold,
            severity=request.severity or "medium",
            save_record=request.save_record if request.save_record is not None else True,
            db=db,
        )
        return response_data
    except Exception as e:
        logger.exception("Error executing mitigation retrieval for alert: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve mitigations: {str(e)}",
        )


@router.post("/answer", response_model=MitigationAnswerResponse, summary="Generate grounded AI mitigation answer for an active security alert")
def answer_mitigation(
    request: MitigationAnswerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generates a concise, grounded mitigation answer for an active security alert using RAG.

    Flow:
    - User Alert -> FAISS semantic retrieval -> Relevant document chunks
    - Synthesizes concise answer ONLY from retrieved context (zero hallucination)
    - Attributes recommendations directly to source documents
    - Keeps retrieved source chunks available alongside the AI answer
    - Returns 'Insufficient information found in the available security documents.' if no relevant context exists
    """
    # 1. Validate alert text
    if not request.alert or not request.alert.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Alert text cannot be empty.",
        )

    # 2. Validate top_k parameter
    top_k = request.top_k if request.top_k is not None else 5
    if top_k < 1 or top_k > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="top_k must be an integer between 1 and 100.",
        )

    # 3. Validate min_threshold parameter
    min_threshold = request.min_threshold if request.min_threshold is not None else 0.35
    if min_threshold < 0.0 or min_threshold > 1.0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="min_threshold must be a float between 0.0 and 1.0.",
        )

    # 4. Execute RAG answer generation
    try:
        rag_service = get_rag_service()
        response_data = rag_service.generate_mitigation_answer(
            alert=request.alert,
            top_k=top_k,
            min_threshold=min_threshold,
            severity=request.severity or "medium",
            db=db,
        )
        return response_data
    except Exception as e:
        logger.exception("Error generating RAG answer for alert: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate mitigation answer: {str(e)}",
        )
