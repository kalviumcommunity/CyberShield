import os
import sys
from fastapi.testclient import TestClient

# Add parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.database import Base, engine, SessionLocal
from app.models import Document, DocumentChunk, DocumentType
from app.services.embedding_service import (
    EMBEDDING_DIMENSION,
    deserialize_embedding,
    generate_embedding,
    generate_embeddings_batch,
    serialize_embedding,
)

client = TestClient(app)


def test_embedding_generation_unit():
    """
    Unit test verifying vector generation, dimension consistency (384), and serialization.
    """
    print("\n[Unit Test 1] Single Text Embedding Generation & Dimension Consistency...")
    sample_text = "CyberShield Security Mitigation: Patch CVE-2026-12345 immediately."
    vector = generate_embedding(sample_text)

    assert isinstance(vector, list), "Expected vector to be a list of floats"
    assert len(vector) == EMBEDDING_DIMENSION, f"Expected {EMBEDDING_DIMENSION} dimensions, got {len(vector)}"
    assert all(isinstance(x, float) for x in vector), "Expected all elements to be floats"
    print(f"[OK] Generated single embedding with consistent dimension: {len(vector)}")

    print("\n[Unit Test 2] Batch Embedding Generation & Serialization...")
    texts = [
        "First cybersecurity threat advisory chunk.",
        "Second incident runbook remediation step.",
    ]
    batch_vectors = generate_embeddings_batch(texts)
    assert len(batch_vectors) == 2
    assert len(batch_vectors[0]) == EMBEDDING_DIMENSION
    assert len(batch_vectors[1]) == EMBEDDING_DIMENSION

    serialized = serialize_embedding(batch_vectors[0])
    deserialized = deserialize_embedding(serialized)
    assert len(deserialized) == EMBEDDING_DIMENSION
    assert abs(deserialized[0] - batch_vectors[0][0]) < 1e-5
    print("[OK] Batch embeddings and serialization verified.")


def test_embeddings_integration_suite():
    print("\n=== Running Day 5 Embedding Generation Integration Tests ===")
    Base.metadata.create_all(bind=engine)

    # 1. Upload sample document
    print("\n[Test 1] Uploading sample security document...")
    upload_resp = client.post(
        "/api/documents/upload",
        data={"document_type": "vulnerability_advisory", "title": "Day 5 Embedding Advisory"},
        files={"file": ("day5_advisory.txt", b"Critical security vulnerability advisory CVE-2026-9999. Apply security patch immediately.", "text/plain")}
    )
    assert upload_resp.status_code == 201, f"Upload failed: {upload_resp.text}"
    doc_id = upload_resp.json()["document_id"]
    print(f"[OK] Document uploaded. ID: {doc_id}")

    # 2. Process document into chunks
    print(f"\n[Test 2] Processing document {doc_id} into chunks...")
    process_resp = client.post(f"/api/documents/{doc_id}/process")
    assert process_resp.status_code == 200, f"Processing failed: {process_resp.text}"
    chunks_created = process_resp.json()["chunks_created"]
    print(f"[OK] Document processed into {chunks_created} chunk(s).")

    # 3. Generate embeddings: POST /api/documents/{doc_id}/embed
    print(f"\n[Test 3] POST /api/documents/{doc_id}/embed...")
    embed_resp = client.post(f"/api/documents/{doc_id}/embed")
    assert embed_resp.status_code == 200, f"Embedding failed: {embed_resp.text}"
    embed_data = embed_resp.json()
    assert embed_data["document_id"] == doc_id
    assert embed_data["chunks_embedded"] == chunks_created
    assert embed_data["embedding_dimension"] == 384
    assert embed_data["status"] == "success"
    print(f"[OK] Generated embeddings for {chunks_created} chunk(s) with dimension {embed_data['embedding_dimension']}.")

    # 4. Verify stored embeddings in PostgreSQL database
    print(f"\n[Test 4] Verifying stored vector embeddings in PostgreSQL...")
    db = SessionLocal()
    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).all()
    assert len(chunks) == chunks_created
    for c in chunks:
        assert c.embedding is not None
        vector = deserialize_embedding(c.embedding)
        assert len(vector) == 384
    db.close()
    print("[OK] Database chunks verified with valid 384-dimensional vector embeddings.")

    # 5. Test duplicate embedding prevention (force=False)
    print(f"\n[Test 5] Testing duplicate embedding prevention (force=False)...")
    dup_embed_resp = client.post(f"/api/documents/{doc_id}/embed")
    assert dup_embed_resp.status_code == 200
    dup_data = dup_embed_resp.json()
    assert dup_data["status"] == "already_embedded"
    assert dup_data["chunks_embedded"] == chunks_created
    print("[OK] Duplicate embedding generation prevented. Status: 'already_embedded'.")

    # 6. Test force embedding regeneration (force=True)
    print(f"\n[Test 6] Testing force embedding regeneration (force=True)...")
    force_embed_resp = client.post(f"/api/documents/{doc_id}/embed?force=true")
    assert force_embed_resp.status_code == 200
    force_data = force_embed_resp.json()
    assert force_data["status"] == "success"
    print("[OK] Force embedding regeneration succeeded. Status: 'success'.")

    # 7. Test Error Handling: 404 for missing document
    print(f"\n[Test 7] Error handling for non-existent document ID 999999...")
    not_found_resp = client.post("/api/documents/999999/embed")
    assert not_found_resp.status_code == 404
    print("[OK] Returned 404 for missing document.")

    # 8. Test Error Handling: 400 for unchunked document
    print(f"\n[Test 8] Error handling for unchunked document...")
    unchunked_upload = client.post(
        "/api/documents/upload",
        data={"document_type": "threat_intelligence"},
        files={"file": ("unchunked.txt", b"Unchunked content text.", "text/plain")}
    )
    unchunked_id = unchunked_upload.json()["document_id"]
    unchunked_embed_resp = client.post(f"/api/documents/{unchunked_id}/embed")
    assert unchunked_embed_resp.status_code == 400
    assert "no chunks" in unchunked_embed_resp.json()["detail"].lower()
    print("[OK] Returned 400 for unchunked document.")

    print("\n=== All Day 5 Embedding Tests Passed Successfully! ===")
    return True


if __name__ == "__main__":
    test_embedding_generation_unit()
    test_embeddings_integration_suite()
