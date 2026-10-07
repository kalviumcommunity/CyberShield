import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.models import Alert, MitigationResult
from app.services.vector_search_service import get_vector_search_service

logger = logging.getLogger("cybershield.mitigation_service")

# Default minimum similarity score threshold to filter out irrelevant noise
DEFAULT_MIN_RELEVANCE_THRESHOLD = 0.30


class MitigationService:
    """
    Cybersecurity Mitigation Retrieval Service.
    Maps active security alerts to actionable, verbatim mitigation steps extracted
    from ingested incident runbooks, threat intelligence reports, and vulnerability advisories.
    """

    def __init__(self):
        self.vector_search_service = get_vector_search_service()

    def search_mitigations(
        self,
        alert: str,
        top_k: int = 5,
        min_threshold: float = DEFAULT_MIN_RELEVANCE_THRESHOLD,
        severity: str = "medium",
        save_record: bool = True,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves relevant mitigation steps from indexed cybersecurity documents for an active alert.

        Args:
            alert: Active security alert description (e.g. suspicious activity, IOCs).
            top_k: Maximum number of relevant chunks to retrieve.
            min_threshold: Minimum semantic relevance score (0.0 to 1.0).
            severity: Alert severity (e.g. low, medium, high, critical).
            save_record: Whether to log the alert and mitigation links in PostgreSQL.
            db: SQLAlchemy Session.

        Returns:
            Dictionary matching the required schema:
            {
                "alert": alert,
                "results": [
                    {
                        "document_id": int,
                        "document_title": str,
                        "document_type": str,
                        "chunk_id": int,
                        "mitigation_text": str,
                        "relevance_score": float,
                        "source_file": str
                    }
                ],
                "total_results": int,
                "alert_id": Optional[int]
            }
        """
        clean_alert = alert.strip()
        if not clean_alert:
            return {"alert": alert, "results": [], "total_results": 0, "alert_id": None}

        # 1. Retrieve candidate chunks via FAISS semantic vector search
        raw_chunks = self.vector_search_service.search(
            query=clean_alert,
            top_k=top_k,
            db=db,
        )

        # 2. Filter by minimum relevance threshold and sort descending by score
        filtered_results = [
            chunk for chunk in raw_chunks
            if chunk.get("relevance_score", 0.0) >= min_threshold
        ]
        filtered_results.sort(key=lambda x: x.get("relevance_score", 0.0), reverse=True)

        # 3. Format structured mitigation outputs preserving source document evidence
        mitigation_items: List[Dict[str, Any]] = []
        for item in filtered_results:
            mitigation_items.append({
                "document_id": item["document_id"],
                "document_title": item["document_title"],
                "document_type": item.get("document_type", "incident_runbook"),
                "chunk_id": item["chunk_id"],
                "mitigation_text": item.get("chunk_content", item.get("content", "")),
                "relevance_score": item["relevance_score"],
                "source_file": item.get("file_name"),
            })

        # 4. Store audit record in PostgreSQL if requested and db session provided
        alert_id: Optional[int] = None
        if save_record and db is not None:
            try:
                alert_title = clean_alert[:250] if len(clean_alert) > 250 else clean_alert
                new_alert = Alert(
                    title=alert_title,
                    description=clean_alert,
                    severity=severity or "medium",
                )
                db.add(new_alert)
                db.flush()  # Populates new_alert.id without committing transaction yet

                for m in mitigation_items:
                    mitigation_record = MitigationResult(
                        alert_id=new_alert.id,
                        document_id=m["document_id"],
                        chunk_id=m["chunk_id"],
                        mitigation_text=m["mitigation_text"],
                        relevance_score=m["relevance_score"],
                    )
                    db.add(mitigation_record)

                db.commit()
                alert_id = new_alert.id
                logger.info(
                    "Logged Alert %s with %d mitigation result(s) in PostgreSQL.",
                    alert_id, len(mitigation_items)
                )
            except Exception as e:
                db.rollback()
                logger.warning("Failed to store Alert and MitigationResult in DB: %s", e)

        return {
            "alert": clean_alert,
            "results": mitigation_items,
            "total_results": len(mitigation_items),
            "alert_id": alert_id,
        }


# Singleton service instance
_mitigation_service_instance: Optional[MitigationService] = None


def get_mitigation_service() -> MitigationService:
    """
    Returns the singleton instance of MitigationService.
    """
    global _mitigation_service_instance
    if _mitigation_service_instance is None:
        _mitigation_service_instance = MitigationService()
    return _mitigation_service_instance
