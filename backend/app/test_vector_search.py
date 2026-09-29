import os
import sys
import numpy as np
import faiss
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Document, DocumentChunk, DocumentType
from app.services.embedding_service import (
    EMBEDDING_DIMENSION,
    generate_embedding,
    generate_embeddings_batch,
    serialize_embedding,
)
from app.services.vector_search_service import (
    VectorSearchService,
    get_vector_search_service,
    search,
)

client = TestClient(app)


def setup_sample_security_corpus(db):
    """
    Seeds comprehensive cybersecurity runbooks and advisories
    matching the evaluation queries.
    """
    corpus = [
        {
            "title": "Endpoint Isolation and Incident Response Runbook",
            "document_type": DocumentType.INCIDENT_RUNBOOK,
            "filename": "endpoint_isolation_runbook.txt",
            "content": (
                "Incident Response Runbook: Endpoint Isolation and Host Remediation. "
                "How do I isolate a compromised endpoint? Immediately sever network connectivity "
                "for the compromised workstation or server. Disconnect physical network Ethernet cables "
                "and disable all active Wi-Fi adapters. On Windows hosts, execute host isolation via EDR "
                "agent or PowerShell to block all inbound and outbound IP traffic except security telemetry. "
                "Terminate unauthorized sessions, invalidate Active Directory Kerberos tickets, and freeze "
                "malicious process hierarchies. Capture volatile memory artifacts before powering down the host."
            ),
        },
        {
            "title": "SQL Injection Mitigation and Remediation Advisory",
            "document_type": DocumentType.VULNERABILITY_ADVISORY,
            "filename": "sql_injection_mitigation.txt",
            "content": (
                "Vulnerability Advisory: Mitigating SQL Injection Flaws. "
                "SQL injection vulnerabilities occur when untrusted user input is concatenated into dynamic SQL queries. "
                "To mitigate and remediate SQL injection vulnerabilities: Always implement parameterized queries "
                "and prepared statements using ORM frameworks. Enforce strict input validation with positive allowlists. "
                "Deploy Web Application Firewall (WAF) signatures to detect and block SQL injection payload patterns. "
                "Apply the principle of least privilege to database service accounts, disabling xp_cmdshell and file write access."
            ),
        },
        {
            "title": "Ransomware Containment and Recovery Guidelines",
            "document_type": DocumentType.INCIDENT_RUNBOOK,
            "filename": "ransomware_response_guide.txt",
            "content": (
                "Standard Operating Procedures: Steps to respond to ransomware activity. "
                "When active ransomware encryption is identified in the environment: "
                "1. Immediately disconnect and quarantine infected subnetworks to halt lateral encryption spread. "
                "2. Kill malicious ransomware binaries, scheduled tasks, and command-and-control communication channels. "
                "3. Locate patient zero by inspecting domain controller authentication logs and VPN connection histories. "
                "4. Preserve encrypted sample files and ransom notes for threat intelligence and law enforcement reporting. "
                "5. Restore operational data from immutable offline backups and verify cryptographic integrity before re-enabling services."
            ),
        },
    ]

    created_chunks = []
    for item in corpus:
        # Check if already exists
        existing_doc = db.query(Document).filter(Document.title == item["title"]).first()
        if not existing_doc:
            doc = Document(
                title=item["title"],
                document_type=item["document_type"],
                file_name=item["filename"],
                file_path=f"uploads/{item['filename']}",
                content=item["content"],
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
        else:
            doc = existing_doc

        # Check chunk
        existing_chunk = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).first()
        if not existing_chunk:
            vec = generate_embedding(doc.content)
            chunk = DocumentChunk(
                document_id=doc.id,
                chunk_index=0,
                content=doc.content,
                embedding=serialize_embedding(vec),
            )
            db.add(chunk)
            db.commit()
            db.refresh(chunk)
            created_chunks.append(chunk)
        else:
            if not existing_chunk.embedding:
                vec = generate_embedding(existing_chunk.content)
                existing_chunk.embedding = serialize_embedding(vec)
                db.commit()
            created_chunks.append(existing_chunk)

    return created_chunks


def test_faiss_configuration():
    """
    Test 1: Verify FAISS installation, configuration, and IndexFlatIP cosine similarity mechanics.
    """
    print("\n--- Test 1: FAISS Installation and IndexFlatIP Configuration ---")
    assert hasattr(faiss, "IndexFlatIP"), "FAISS must support IndexFlatIP"
    index = faiss.IndexFlatIP(EMBEDDING_DIMENSION)
    assert index.d == EMBEDDING_DIMENSION, f"Index dimension must be {EMBEDDING_DIMENSION}"
    assert index.ntotal == 0, "Index must start empty"

    # Test normalization and inner product cosine similarity
    v1 = np.random.randn(1, EMBEDDING_DIMENSION).astype(np.float32)
    faiss.normalize_L2(v1)
    index.add(v1)
    assert index.ntotal == 1

    dists, idxs = index.search(v1, 1)
    assert idxs[0][0] == 0
    assert abs(dists[0][0] - 1.0) < 1e-4, f"Self-similarity should be 1.0, got {dists[0][0]}"
    print("[PASS] FAISS configured properly with normalized cosine similarity.")


def test_empty_faiss_index_handling():
    """
    Test 2: Handle empty FAISS index gracefully without crashing or 500 errors.
    """
    print("\n--- Test 2: Empty FAISS Index Graceful Handling ---")
    service = VectorSearchService(dimension=EMBEDDING_DIMENSION)
    service.clear_index()
    assert service.total_vectors == 0

    # Search against empty service
    results = service.search("compromised endpoint", top_k=5)
    assert isinstance(results, list), "Expected list response for empty index"
    assert len(results) == 0, f"Expected 0 results for empty index, got {len(results)}"
    print("[PASS] Empty index handled gracefully, returning empty list.")


def test_index_building_and_mapping():
    """
    Test 3: Build index and verify FAISS vector index -> DocumentChunk ID mapping.
    """
    print("\n--- Test 3: FAISS Vector Index to DocumentChunk ID Mapping ---")
    db = SessionLocal()
    try:
        setup_sample_security_corpus(db)
        service = get_vector_search_service()
        indexed_count = service.rebuild_index(db)
        assert indexed_count > 0, "Expected at least 1 indexed chunk"

        mapping = service.get_mapping()
        assert len(mapping) == indexed_count
        assert len(service.index_to_chunk_id) == indexed_count

        for faiss_idx, chunk_id in mapping.items():
            assert isinstance(faiss_idx, int)
            assert isinstance(chunk_id, int)
            assert service.get_chunk_id_by_index(faiss_idx) == chunk_id

            # Verify chunk exists in database
            chunk = db.query(DocumentChunk).filter(DocumentChunk.id == chunk_id).first()
            assert chunk is not None, f"Chunk {chunk_id} must exist in DB"
            assert chunk.embedding is not None, f"Chunk {chunk_id} must have embedding"

        print(f"[PASS] Successfully mapped {indexed_count} FAISS vector rows to DocumentChunk IDs.")
    finally:
        db.close()


def test_semantic_search_function():
    """
    Test 4: Verify search(query, top_k) function and required returned fields.
    """
    print("\n--- Test 4: Semantic Search Function Output Structure ---")
    db = SessionLocal()
    try:
        service = get_vector_search_service()
        service.ensure_initialized(db)

        results = search("compromised endpoint isolation", top_k=3, db=db)
        assert len(results) > 0, "Expected at least one result"

        required_fields = [
            "chunk_id",
            "document_id",
            "document_title",
            "chunk_content",
            "similarity_score",
            "relevance_score",
        ]

        for item in results:
            for field in required_fields:
                assert field in item, f"Missing required field: {field}"
            assert isinstance(item["chunk_id"], int)
            assert isinstance(item["document_id"], int)
            assert isinstance(item["document_title"], str)
            assert isinstance(item["chunk_content"], str)
            assert isinstance(item["similarity_score"], float)
            assert isinstance(item["relevance_score"], float)
            assert 0.0 <= item["similarity_score"] <= 1.0
            assert 0.0 <= item["relevance_score"] <= 1.0

        # Ensure sorted in descending order of relevance
        scores = [item["relevance_score"] for item in results]
        assert scores == sorted(scores, reverse=True), "Results must be ranked in descending score order"
        print("[PASS] Semantic search returns all required fields and correct descending rank.")
    finally:
        db.close()


def test_example_security_queries():
    """
    Test 5: Verify the three required example queries from the prompt:
    - "How do I isolate a compromised endpoint?"
    - "How do I mitigate a SQL injection vulnerability?"
    - "Steps to respond to ransomware activity"
    """
    print("\n--- Test 5: Semantic Search with Benchmark Security Queries ---")
    db = SessionLocal()
    try:
        service = get_vector_search_service()
        service.ensure_initialized(db)

        test_cases = [
            {
                "query": "How do I isolate a compromised endpoint?",
                "expected_keyword": "endpoint",
                "expected_topic": "isolation",
            },
            {
                "query": "How do I mitigate a SQL injection vulnerability?",
                "expected_keyword": "sql",
                "expected_topic": "injection",
            },
            {
                "query": "Steps to respond to ransomware activity",
                "expected_keyword": "ransomware",
                "expected_topic": "ransomware",
            },
        ]

        for case in test_cases:
            query = case["query"]
            results = service.search(query=query, top_k=3, db=db)
            assert len(results) > 0, f"No results returned for query: '{query}'"

            top_result = results[0]
            print(f"\nQuery: '{query}'")
            print(f"  Top Match Title: {top_result['document_title']}")
            print(f"  Similarity Score: {top_result['similarity_score']:.4f}")
            print(f"  Content Snippet: {top_result['chunk_content'][:120]}...")

            content_lower = (top_result["chunk_content"] + " " + top_result["document_title"]).lower()
            assert case["expected_keyword"] in content_lower, (
                f"Expected '{case['expected_keyword']}' in top result for query '{query}'"
            )
            assert top_result["similarity_score"] > 0.40, (
                f"Expected similarity score > 0.40, got {top_result['similarity_score']}"
            )

        print("\n[PASS] All 3 benchmark security queries retrieved highly relevant document chunks.")
    finally:
        db.close()


def test_api_search_endpoint():
    """
    Test 6: Test GET /api/search?q=<query>&top_k=5 API endpoint and query validation.
    """
    print("\n--- Test 6: API Endpoint GET /api/search Validation & Results ---")
    login_resp = client.post("/api/auth/login", json={"email": "analyst@cybershield.io", "password": "AnalystPass123!"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Valid search
    resp = client.get("/api/search?q=How%20do%20I%20isolate%20a%20compromised%20endpoint?&top_k=3", headers=headers)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    first = data[0]
    assert "chunk_id" in first
    assert "document_id" in first
    assert "document_title" in first
    assert "chunk_content" in first
    assert "similarity_score" in first
    assert "relevance_score" in first
    print("[PASS] GET /api/search returned valid JSON list with required fields.")

    # 2. Empty query validation (empty string)
    empty_resp = client.get("/api/search?q=", headers=headers)
    assert empty_resp.status_code == 400, f"Expected 400 for empty query, got {empty_resp.status_code}"
    print("[PASS] Empty query correctly rejected with 400 Bad Request.")

    # 3. Whitespace query validation
    ws_resp = client.get("/api/search?q=%20%20%20", headers=headers)
    assert ws_resp.status_code == 400, f"Expected 400 for whitespace query, got {ws_resp.status_code}"
    print("[PASS] Whitespace query correctly rejected with 400 Bad Request.")

    # 4. Missing query parameter
    missing_resp = client.get("/api/search", headers=headers)
    assert missing_resp.status_code == 400, f"Expected 400 for missing query, got {missing_resp.status_code}"
    print("[PASS] Missing 'q' parameter rejected with 400 Bad Request.")

    # 5. Invalid top_k (< 1)
    invalid_k_resp = client.get("/api/search?q=ransomware&top_k=0", headers=headers)
    assert invalid_k_resp.status_code == 400, f"Expected 400 for top_k=0, got {invalid_k_resp.status_code}"
    print("[PASS] Invalid top_k=0 rejected with 400 Bad Request.")

    # 6. Invalid top_k (> 100)
    invalid_k2_resp = client.get("/api/search?q=ransomware&top_k=150", headers=headers)
    assert invalid_k2_resp.status_code == 400, f"Expected 400 for top_k=150, got {invalid_k2_resp.status_code}"
    print("[PASS] Invalid top_k=150 rejected with 400 Bad Request.")


def test_rebuild_index_endpoint():
    """
    Test 7: Test POST /api/search/rebuild endpoint.
    """
    print("\n--- Test 7: Index Rebuild Endpoint POST /api/search/rebuild ---")
    login_resp = client.post("/api/auth/login", json={"email": "admin@cybershield.io", "password": "AdminPass123!"})
    token = login_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {token}"}

    resp = client.post("/api/search/rebuild?auto_embed=true", headers=admin_headers)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["status"] == "success"
    assert body["indexed_chunks"] > 0
    print(f"[PASS] Index rebuild succeeded with {body['indexed_chunks']} indexed chunks.")


def run_all_day6_tests():
    print("=" * 70)
    print("      CYBERSHIELD DAY 6 - FAISS SEMANTIC SEARCH TEST SUITE      ")
    print("=" * 70)

    Base.metadata.create_all(bind=engine)
    test_faiss_configuration()
    test_empty_faiss_index_handling()
    test_index_building_and_mapping()
    test_semantic_search_function()
    test_example_security_queries()
    test_api_search_endpoint()
    test_rebuild_index_endpoint()

    print("\n" + "=" * 70)
    print("      ALL DAY 6 SEMANTIC VECTOR SEARCH TESTS PASSED!            ")
    print("=" * 70)


if __name__ == "__main__":
    run_all_day6_tests()
