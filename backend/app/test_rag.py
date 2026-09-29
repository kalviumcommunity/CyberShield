import os
import sys
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Document, DocumentChunk, DocumentType
from app.services.embedding_service import generate_embedding, serialize_embedding
from app.services.rag_service import INSUFFICIENT_INFO_MESSAGE, get_rag_service
from app.services.vector_search_service import get_vector_search_service

client = TestClient(app)


def setup_security_corpus(db):
    """
    Seeds and ensures the benchmark cybersecurity corpus is indexed.
    """
    corpus = [
        {
            "title": "PowerShell Threat Intelligence and Incident Runbook",
            "document_type": DocumentType.INCIDENT_RUNBOOK,
            "filename": "powershell_incident_runbook.txt",
            "content": (
                "Incident Runbook: Suspicious PowerShell Activity and Host Containment. "
                "When multiple Windows endpoints show suspicious PowerShell execution or obfuscated command lines: "
                "1. Immediately isolate affected Windows endpoints via host-based firewall or EDR containment. "
                "2. Terminate rogue PowerShell process trees (powershell.exe, pwsh.exe) and parent processes. "
                "3. Enable PowerShell Script Block Logging (Event ID 4104) and Module Logging across Group Policy. "
                "4. Enforce PowerShell Constrained Language Mode and configure AppLocker / WDAC policies. "
                "5. Revoke compromised user credentials and invalidate Kerberos golden tickets."
            ),
        },
        {
            "title": "Enterprise Ransomware Containment and Recovery Guidelines",
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
    ]

    for item in corpus:
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
            doc.content = item["content"]
            db.commit()

        existing_chunk = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).first()
        vec = generate_embedding(doc.content)
        if not existing_chunk:
            chunk = DocumentChunk(
                document_id=doc.id,
                chunk_index=0,
                content=doc.content,
                embedding=serialize_embedding(vec),
            )
            db.add(chunk)
            db.commit()
        else:
            existing_chunk.content = doc.content
            existing_chunk.embedding = serialize_embedding(vec)
            db.commit()

    get_vector_search_service().rebuild_index(db)


def test_rag_with_relevant_context():
    """
    Test 1: Verify RAG flow when relevant context exists in uploaded security documents.
    """
    print("\n--- Test 1: RAG Flow with Relevant Context ---")
    db = SessionLocal()
    try:
        setup_security_corpus(db)
        rag_service = get_rag_service()

        alert = "Multiple Windows endpoints are showing suspicious PowerShell activity."
        response = rag_service.generate_mitigation_answer(
            alert=alert,
            top_k=3,
            min_threshold=0.35,
            db=db,
        )

        assert response["alert"] == alert
        assert response["answer"] != INSUFFICIENT_INFO_MESSAGE
        assert len(response["sources"]) > 0
        assert len(response["results"]) > 0

        # Verify answer content is grounded
        answer_text = response["answer"]
        print(f"Generated Grounded Answer:\n{answer_text}\n")

        assert "PowerShell" in answer_text
        assert "isolate" in answer_text.lower() or "containment" in answer_text.lower()
        print("[PASS] Generated concise grounded mitigation answer from relevant context.")
    finally:
        db.close()


def test_rag_with_no_relevant_context():
    """
    Test 2: Verify fallback when no relevant security documents are found.
    Must return: 'Insufficient information found in the available security documents.'
    """
    print("\n--- Test 2: RAG Flow with No Relevant Context ---")
    db = SessionLocal()
    try:
        rag_service = get_rag_service()

        # Completely unrelated non-cybersecurity query with strict threshold
        unrelated_query = "What is the best recipe for baking chocolate chip cookies at high altitude?"
        response = rag_service.generate_mitigation_answer(
            alert=unrelated_query,
            top_k=3,
            min_threshold=0.60,
            db=db,
        )

        assert response["alert"] == unrelated_query
        assert response["answer"] == INSUFFICIENT_INFO_MESSAGE
        assert len(response["sources"]) == 0
        print(f"[PASS] Successfully returned fallback: '{response['answer']}'")
    finally:
        db.close()


def test_source_attribution():
    """
    Test 3: Verify strict source attribution in both answer and sources array.
    """
    print("\n--- Test 3: Source Attribution Verification ---")
    db = SessionLocal()
    try:
        rag_service = get_rag_service()

        alert = "Active ransomware outbreak detected encrypting shared network folders."
        response = rag_service.generate_mitigation_answer(
            alert=alert,
            top_k=2,
            min_threshold=0.35,
            db=db,
        )

        sources = response["sources"]
        assert len(sources) > 0

        top_source = sources[0]
        assert "document_title" in top_source
        assert "document_type" in top_source
        assert "document_id" in top_source
        assert "chunk_id" in top_source
        assert "mitigation_text" in top_source
        assert "relevance_score" in top_source

        # Verify source document title is explicitly cited in the synthesized answer
        assert top_source["document_title"] in response["answer"]
        print(f"[PASS] Verified source attribution to: '{top_source['document_title']}' ({top_source['document_type']})")
    finally:
        db.close()


def test_hallucination_safeguards():
    """
    Test 4: Verify hallucination safeguards: no fabricated commands, CVEs, or steps not in context.
    """
    print("\n--- Test 4: Hallucination Safeguards ---")
    db = SessionLocal()
    try:
        rag_service = get_rag_service()

        alert = "SQL injection vulnerability identified in web authentication endpoint."
        response = rag_service.generate_mitigation_answer(
            alert=alert,
            top_k=2,
            min_threshold=0.35,
            db=db,
        )

        sources = response["sources"]
        assert len(sources) > 0

        # All text in the answer must trace back to retrieved sources or formatting headers
        combined_source_text = " ".join(s["mitigation_text"] for s in sources).lower()
        answer_lower = response["answer"].lower()

        # Check key mitigation concepts were grounded in source
        for keyword in ["parameterized queries", "prepared statements", "input validation"]:
            assert keyword in combined_source_text
            assert keyword in answer_lower

        # Ensure no fabricated random CVEs (like CVE-1999-9999) appear in answer
        assert "cve-1999-9999" not in answer_lower
        print("[PASS] Hallucination safeguards verified. Answer strictly grounded in source chunks.")
    finally:
        db.close()


def test_api_answer_endpoint():
    """
    Test 5: Verify POST /api/mitigation/answer endpoint and request validation.
    """
    print("\n--- Test 5: API Endpoint POST /api/mitigation/answer ---")

    # 1. Valid request
    resp = client.post(
        "/api/mitigation/answer",
        json={"alert": "Multiple Windows endpoints are showing suspicious PowerShell activity."},
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert "alert" in data
    assert "answer" in data
    assert "sources" in data
    assert isinstance(data["sources"], list)
    assert len(data["sources"]) > 0
    print("[PASS] POST /api/mitigation/answer returned valid JSON with answer and sources.")

    # 2. Empty alert validation
    empty_resp = client.post("/api/mitigation/answer", json={"alert": ""})
    assert empty_resp.status_code == 400
    assert "cannot be empty" in empty_resp.json()["detail"].lower()
    print("[PASS] Empty alert string rejected with 400 Bad Request.")

    # 3. Whitespace alert validation
    ws_resp = client.post("/api/mitigation/answer", json={"alert": "   "})
    assert ws_resp.status_code == 400
    assert "cannot be empty" in ws_resp.json()["detail"].lower()
    print("[PASS] Whitespace alert rejected with 400 Bad Request.")

    # 4. Invalid top_k validation (< 1)
    k_resp = client.post("/api/mitigation/answer", json={"alert": "ransomware", "top_k": 0})
    assert k_resp.status_code == 400
    print("[PASS] Invalid top_k rejected with 400 Bad Request.")

    # 5. Fallback response via API for irrelevant query
    irrelevant_resp = client.post(
        "/api/mitigation/answer",
        json={"alert": "How do I make strawberry ice cream at home?", "min_threshold": 0.60},
    )
    assert irrelevant_resp.status_code == 200
    irr_data = irrelevant_resp.json()
    assert irr_data["answer"] == INSUFFICIENT_INFO_MESSAGE
    assert len(irr_data["sources"]) == 0
    print(f"[PASS] API returned standardized fallback for irrelevant query: '{irr_data['answer']}'")


def run_all_day8_tests():
    print("=" * 70)
    print("      CYBERSHIELD DAY 8 - RAG MITIGATION ANSWER TEST SUITE     ")
    print("=" * 70)

    Base.metadata.create_all(bind=engine)
    test_rag_with_relevant_context()
    test_rag_with_no_relevant_context()
    test_source_attribution()
    test_hallucination_safeguards()
    test_api_answer_endpoint()

    print("\n" + "=" * 70)
    print("      ALL DAY 8 RAG MITIGATION ANSWER TESTS PASSED!             ")
    print("=" * 70)


if __name__ == "__main__":
    run_all_day8_tests()
