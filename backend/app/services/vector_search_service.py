import json
import logging
from typing import Any, Dict, List, Optional, Tuple
import faiss
import numpy as np
from sqlalchemy.orm import Session, joinedload

from app.database import SessionLocal
from app.models import DocumentChunk
from app.services.embedding_service import (
    EMBEDDING_DIMENSION,
    deserialize_embedding,
    generate_embedding,
    generate_embeddings_batch,
    serialize_embedding,
)

logger = logging.getLogger("cybershield.vector_search")


class VectorSearchService:
    """
    Semantic Vector Search Service powered by FAISS and Sentence Transformers.
    Manages FAISS vector indexing, internal index to DocumentChunk ID mappings,
    real-time index rebuilding, and cosine similarity semantic retrieval.
    """

    def __init__(self, dimension: int = EMBEDDING_DIMENSION):
        self.dimension = dimension
        self.index: Optional[faiss.Index] = None
        self.index_to_chunk_id: List[int] = []
        self.chunk_id_to_index: Dict[int, int] = {}
        self._is_initialized: bool = False
        self._initialize_empty_index()

    def _initialize_empty_index(self) -> None:
        """
        Creates an empty FAISS IndexFlatIP (Inner Product) index for cosine similarity.
        """
        self.index = faiss.IndexFlatIP(self.dimension)
        self.index_to_chunk_id = []
        self.chunk_id_to_index = {}

    @property
    def total_vectors(self) -> int:
        """
        Returns the current number of indexed vectors in FAISS.
        """
        return self.index.ntotal if self.index is not None else 0

    def get_chunk_id_by_index(self, faiss_idx: int) -> Optional[int]:
        """
        Returns the DocumentChunk ID for a given FAISS vector index position.
        """
        if 0 <= faiss_idx < len(self.index_to_chunk_id):
            return self.index_to_chunk_id[faiss_idx]
        return None

    def get_mapping(self) -> Dict[int, int]:
        """
        Returns the full mapping of FAISS vector index -> DocumentChunk ID.
        """
        return {idx: chunk_id for idx, chunk_id in enumerate(self.index_to_chunk_id)}

    def clear_index(self) -> None:
        """
        Clears the FAISS index and resets the mappings.
        """
        self._initialize_empty_index()
        self._is_initialized = True

    def build_index(self, db: Session, force: bool = False) -> int:
        """
        Builds the FAISS index from all document chunks that have embeddings in the database.
        Maintains a sequential mapping from FAISS vector row index to DocumentChunk ID.
        """
        if self._is_initialized and not force:
            return self.total_vectors

        chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.embedding.isnot(None))
            .order_by(DocumentChunk.id.asc())
            .all()
        )

        vectors: List[List[float]] = []
        chunk_ids: List[int] = []

        for chunk in chunks:
            try:
                vec = deserialize_embedding(chunk.embedding)
                if vec and len(vec) == self.dimension:
                    vectors.append(vec)
                    chunk_ids.append(chunk.id)
            except Exception as e:
                logger.warning("Skipping chunk %s due to invalid embedding: %s", chunk.id, e)

        if vectors:
            vectors_np = np.ascontiguousarray(np.array(vectors, dtype=np.float32))
            faiss.normalize_L2(vectors_np)

            new_index = faiss.IndexFlatIP(self.dimension)
            new_index.add(vectors_np)

            self.index = new_index
            self.index_to_chunk_id = chunk_ids
            self.chunk_id_to_index = {cid: idx for idx, cid in enumerate(chunk_ids)}
        else:
            self._initialize_empty_index()

        self._is_initialized = True
        logger.info("Built FAISS index with %d chunks.", self.total_vectors)
        return self.total_vectors

    def rebuild_index(self, db: Session, auto_embed_unembedded: bool = False) -> int:
        """
        Rebuilds the FAISS index from the database.
        Optionally generates embeddings for any chunks that lack them.
        """
        if auto_embed_unembedded:
            unembedded_chunks = (
                db.query(DocumentChunk)
                .filter(DocumentChunk.embedding.is_(None))
                .all()
            )
            if unembedded_chunks:
                texts = [c.content for c in unembedded_chunks]
                new_vectors = generate_embeddings_batch(texts)
                for chunk, vec in zip(unembedded_chunks, new_vectors):
                    chunk.embedding = serialize_embedding(vec)
                db.commit()

        return self.build_index(db, force=True)

    def ensure_initialized(self, db: Session) -> None:
        """
        Ensures the FAISS index is loaded into memory.
        """
        if not self._is_initialized:
            self.build_index(db)

    def search(
        self,
        query: str,
        top_k: int = 5,
        db: Optional[Session] = None,
    ) -> List[Dict[str, Any]]:
        """
        Performs semantic vector search against document chunks using FAISS.

        Args:
            query: The analyst search query or security alert description.
            top_k: Number of most relevant DocumentChunks to return (must be >= 1).
            db: Optional SQLAlchemy Session. If omitted, a scoped session is used.

        Returns:
            List of dicts containing:
            - chunk_id: DocumentChunk primary key ID
            - document_id: Parent Document ID
            - document_title: Parent Document title
            - chunk_content: Chunk text snippet
            - content: Alias for chunk_content
            - similarity_score: Cosine similarity score (0.0 to 1.0)
            - relevance_score: Cosine relevance score (0.0 to 1.0)
        """
        # 1. Handle empty / whitespace queries gracefully
        if not query or not query.strip():
            return []

        # 2. Validate top_k
        if top_k is None or top_k < 1:
            raise ValueError("top_k must be an integer greater than or equal to 1.")

        top_k = min(top_k, 100)

        # 3. Execute search with database session
        if db is None:
            with SessionLocal() as session:
                return self._execute_search(query.strip(), top_k, session)
        else:
            return self._execute_search(query.strip(), top_k, db)

    def _execute_search(
        self,
        clean_query: str,
        top_k: int,
        db: Session,
    ) -> List[Dict[str, Any]]:
        """
        Internal implementation of FAISS semantic search and document retrieval.
        """
        self.ensure_initialized(db)

        # 4. Handle empty FAISS index gracefully
        if self.index is None or self.index.ntotal == 0:
            logger.info("FAISS index is empty; returning 0 results.")
            return []

        # 5. Convert analyst query into 384-d dense vector embedding
        query_vector = generate_embedding(clean_query)
        q_np = np.ascontiguousarray(np.array([query_vector], dtype=np.float32))
        faiss.normalize_L2(q_np)

        # 6. Determine actual retrieval limit
        actual_k = min(top_k, self.index.ntotal)
        if actual_k <= 0:
            return []

        # 7. Search FAISS index
        distances, indices = self.index.search(q_np, actual_k)
        matched_indices = indices[0]
        matched_scores = distances[0]

        # 8. Map FAISS vector indices to DocumentChunk IDs
        candidate_pairs: List[Tuple[int, float]] = []
        for faiss_idx, score in zip(matched_indices, matched_scores):
            if faiss_idx < 0 or faiss_idx >= len(self.index_to_chunk_id):
                continue
            chunk_id = self.index_to_chunk_id[faiss_idx]
            candidate_pairs.append((chunk_id, float(score)))

        if not candidate_pairs:
            return []

        # 9. Query DocumentChunks and their parent Documents
        chunk_ids = [p[0] for p in candidate_pairs]
        chunks = (
            db.query(DocumentChunk)
            .options(joinedload(DocumentChunk.document))
            .filter(DocumentChunk.id.in_(chunk_ids))
            .all()
        )
        chunk_map = {c.id: c for c in chunks}

        # 10. Construct ordered results matching FAISS ranking
        results: List[Dict[str, Any]] = []
        for chunk_id, score in candidate_pairs:
            chunk_obj = chunk_map.get(chunk_id)
            if not chunk_obj:
                continue

            doc_title = (
                chunk_obj.document.title
                if chunk_obj.document and chunk_obj.document.title
                else "Untitled Document"
            )
            # Normalised inner product is cosine similarity; ensure values are clean floats in [0, 1]
            clamped_score = max(0.0, min(1.0, float(score)))
            rounded_score = round(clamped_score, 4)

            doc_type = (
                chunk_obj.document.document_type.value
                if chunk_obj.document and hasattr(chunk_obj.document.document_type, "value")
                else str(chunk_obj.document.document_type) if chunk_obj.document else "unknown"
            )
            file_name = chunk_obj.document.file_name if chunk_obj.document else None

            results.append({
                "chunk_id": chunk_obj.id,
                "document_id": chunk_obj.document_id,
                "document_title": doc_title,
                "document_type": doc_type,
                "file_name": file_name,
                "chunk_content": chunk_obj.content,
                "content": chunk_obj.content,
                "similarity_score": rounded_score,
                "relevance_score": rounded_score,
            })

        return results


# Global singleton instance
_search_service_instance: Optional[VectorSearchService] = None


def get_vector_search_service() -> VectorSearchService:
    """
    Returns the singleton instance of VectorSearchService.
    """
    global _search_service_instance
    if _search_service_instance is None:
        _search_service_instance = VectorSearchService()
    return _search_service_instance


def search(
    query: str,
    top_k: int = 5,
    db: Optional[Session] = None,
) -> List[Dict[str, Any]]:
    """
    Semantic search function:
    search(query, top_k)

    Converts the analyst query into an embedding, searches the FAISS index,
    and returns the most relevant DocumentChunks.
    """
    return get_vector_search_service().search(query=query, top_k=top_k, db=db)
