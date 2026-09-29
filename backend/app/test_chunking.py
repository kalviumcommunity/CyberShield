import os
import sys
from fastapi.testclient import TestClient

# Add parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.database import Base, engine, SessionLocal
from app.models import Document, DocumentChunk, DocumentType
from app.services.chunking_service import clean_text, chunk_text

client = TestClient(app)


def test_text_cleaning_unit():
    """
    Unit test verifying text cleaning, line break normalization, and security term preservation.
    """
    print("\n[Unit Test 1] Clean Text Normalization & Security Term Preservation...")
    raw_text = (
        "   CyberShield Security Report   \r\n\r\n"
        "Target IP: 192.168.1.100\t\tPort: 443\r\n"
        "Vulnerability: CVE-2026-12345 (Critical Remote Code Execution)\n\n\n\n"
        "Mitigation: Apply patch KB99999 and run powershell -ExecutionPolicy Bypass script.\n"
    )
    cleaned = clean_text(raw_text)

    assert "192.168.1.100" in cleaned
    assert "CVE-2026-12345" in cleaned
    assert "powershell -ExecutionPolicy Bypass" in cleaned
    assert "\r" not in cleaned
    assert "\n\n\n" not in cleaned
    print("[OK] Text cleaning and security term preservation passed.")


def test_chunking_unit():
    """
    Unit test verifying word-based chunking, overlap, and order preservation.
    """
    print("\n[Unit Test 2] Word Chunking & Overlap...")
    # Generate text with 1500 words
    words = [f"word{i}" for i in range(1500)]
    sample_text = " ".join(words)

    chunks = chunk_text(sample_text, target_chunk_size=600, chunk_overlap=60)
    assert len(chunks) > 1, f"Expected multiple chunks, got {len(chunks)}"

    # Verify overlap exists between chunk 0 and chunk 1
    chunk0_words = set(chunks[0].split())
    chunk1_words = set(chunks[1].split())
    common_words = chunk0_words.intersection(chunk1_words)
    assert len(common_words) >= 30, f"Expected overlap between chunks, found {len(common_words)} common words"

    print(f"[OK] Chunking generated {len(chunks)} chunks with verified word overlap.")


def test_chunking_integration_suite():
    print("\n=== Running Day 4 Chunking Integration Tests ===")
    Base.metadata.create_all(bind=engine)

    # 1. Create a sample security document with substantial text (700+ words)
    print("\n[Test 1] Uploading a sample security document for chunking...")
    security_paragraphs = []
    for section in range(1, 15):
        paragraph = (
            f"Section {section}: Cybersecurity Threat Mitigation Advisory for Corporate Systems. "
            f"Active security alert ID SEC-2026-{section:03d} detected suspicious activity from IP address 10.0.0.{section}. "
            f"Analysts must isolate infected hosts, run vulnerability scans for CVE-2026-{section:04d}, "
            f"update firewall rules, and analyze memory dumps. "
            f"Refer to incident runbook IR-{section:02d} for detailed escalation steps and compliance reporting. "
        ) * 5
        security_paragraphs.append(paragraph)

    full_document_text = "\n\n".join(security_paragraphs)

    upload_resp = client.post(
        "/api/documents/upload",
        data={"document_type": "threat_intelligence", "title": "Day 4 Security Comprehensive Advisory"},
        files={"file": ("day4_advisory.txt", full_document_text.encode("utf-8"), "text/plain")}
    )
    assert upload_resp.status_code == 201, f"Upload failed: {upload_resp.text}"
    doc_id = upload_resp.json()["document_id"]
    print(f"[OK] Document uploaded successfully. ID: {doc_id}")

    # 2. Process document into chunks: POST /api/documents/{doc_id}/process
    print(f"\n[Test 2] POST /api/documents/{doc_id}/process...")
    process_resp = client.post(f"/api/documents/{doc_id}/process")
    assert process_resp.status_code == 200, f"Processing failed: {process_resp.text}"
    process_data = process_resp.json()
    assert process_data["document_id"] == doc_id
    assert process_data["processing_status"] == "success"
    assert process_data["chunks_created"] > 0
    chunks_created_count = process_data["chunks_created"]
    print(f"[OK] Document processed successfully into {chunks_created_count} chunk(s).")

    # 3. Verify chunks in PostgreSQL database via GET /api/documents/{doc_id}/chunks
    print(f"\n[Test 3] Verifying stored DocumentChunk records in PostgreSQL...")
    chunks_resp = client.get(f"/api/documents/{doc_id}/chunks")
    assert chunks_resp.status_code == 200, f"GET chunks failed: {chunks_resp.text}"
    chunks_list = chunks_resp.json()
    assert len(chunks_list) == chunks_created_count

    # Check 0-indexed order and content non-emptiness
    for i, chunk in enumerate(chunks_list):
        assert chunk["chunk_index"] == i
        assert chunk["document_id"] == doc_id
        assert len(chunk["content"].strip()) > 0
    print(f"[OK] Verified {len(chunks_list)} DocumentChunk records in DB in correct 0-indexed order.")

    # 4. Test duplicate processing prevention (force=False)
    print(f"\n[Test 4] Testing duplicate processing prevention (force=False)...")
    dup_resp = client.post(f"/api/documents/{doc_id}/process")
    assert dup_resp.status_code == 200
    dup_data = dup_resp.json()
    assert dup_data["processing_status"] == "already_processed"
    assert dup_data["chunks_created"] == chunks_created_count
    print(f"[OK] Duplicate processing prevented. Returned status 'already_processed'.")

    # 5. Test force re-processing (force=True)
    print(f"\n[Test 5] Testing force re-processing (force=True)...")
    force_resp = client.post(f"/api/documents/{doc_id}/process?force=true")
    assert force_resp.status_code == 200
    force_data = force_resp.json()
    assert force_data["processing_status"] == "success"
    assert force_data["chunks_created"] == chunks_created_count
    print(f"[OK] Force re-processing succeeded with status 'success'.")

    # 6. Test Error Handling: 404 for non-existent document
    print(f"\n[Test 6] Error handling for non-existent document ID 999999...")
    not_found_resp = client.post("/api/documents/999999/process")
    assert not_found_resp.status_code == 404
    print(f"[OK] Returned 404 for missing document.")

    # 7. Test Error Handling: 400 for document with empty content
    print(f"\n[Test 7] Error handling for empty document content...")
    db = SessionLocal()
    empty_doc = Document(
        title="Empty Doc",
        document_type=DocumentType.THREAT_INTELLIGENCE,
        file_name="empty.txt",
        file_path="uploads/empty.txt",
        content="",
    )
    db.add(empty_doc)
    db.commit()
    db.refresh(empty_doc)
    empty_id = empty_doc.id
    db.close()

    empty_process_resp = client.post(f"/api/documents/{empty_id}/process")
    assert empty_process_resp.status_code == 400
    assert "empty" in empty_process_resp.json()["detail"].lower()
    print(f"[OK] Returned 400 for empty document content.")

    print("\n=== All Day 4 Chunking Tests Passed Successfully! ===")
    return True


if __name__ == "__main__":
    test_text_cleaning_unit()
    test_chunking_unit()
    success = test_chunking_integration_suite()
    if not success:
        sys.exit(1)
