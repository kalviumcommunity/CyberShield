import os
import sys
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Alert, Document, DocumentChunk, DocumentType, MitigationResult
from app.services.embedding_service import generate_embedding, serialize_embedding
from app.services.mitigation_service import get_mitigation_service
from app.services.vector_search_service import get_vector_search_service

client = TestClient(app)


def setup_security_corpus(db):
    """
    Ensures benchmark security documents covering runbooks, advisories,
    and threat intelligence reports are present and embedded.
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

    # Rebuild FAISS index
    v_service = get_vector_search_service()
    v_service.rebuild_index(db)


def test_mitigation_service_unit():
    """
    Test 1: Unit test MitigationService logic, structure, and relevance sorting.
    """
    print("\n--- Test 1: MitigationService Logic and Structure ---")
    db = SessionLocal()
    try:
        setup_security_corpus(db)
        service = get_mitigation_service()

        alert_text = "Multiple Windows endpoints are showing suspicious PowerShell activity."
        result = service.search_mitigations(
            alert=alert_text,
            top_k=3,
            min_threshold=0.30,
            save_record=False,
            db=db,
        )

        assert result["alert"] == alert_text
        assert "results" in result
        assert len(result["results"]) > 0

        # Check structure of results
        top_item = result["results"][0]
        assert "document_id" in top_item
        assert "document_title" in top_item
        assert "document_type" in top_item
        assert "chunk_id" in top_item
        assert "mitigation_text" in top_item
        assert "relevance_score" in top_item

        # Check sorting
        scores = [r["relevance_score"] for r in result["results"]]
        assert scores == sorted(scores, reverse=True), "Results must be sorted descending by relevance score"

        print(f"[PASS] Top match: '{top_item['document_title']}' with score {top_item['relevance_score']:.4f}")
    finally:
        db.close()


def test_minimum_relevance_threshold():
    """
    Test 2: Verify minimum relevance threshold filters out low-similarity chunks.
    """
    print("\n--- Test 2: Minimum Relevance Threshold Filtering ---")
    db = SessionLocal()
    try:
        service = get_mitigation_service()
        alert_text = "Multiple Windows endpoints are showing suspicious PowerShell activity."

        # High threshold that nothing should pass
        strict_result = service.search_mitigations(
            alert=alert_text,
            top_k=5,
            min_threshold=0.99,
            save_record=False,
            db=db,
        )
        assert len(strict_result["results"]) == 0, "High threshold (0.99) should yield 0 results"

        # Reasonable threshold (0.30)
        normal_result = service.search_mitigations(
            alert=alert_text,
            top_k=5,
            min_threshold=0.30,
            save_record=False,
            db=db,
        )
        assert len(normal_result["results"]) > 0, "Standard threshold (0.30) should yield matching results"
        for r in normal_result["results"]:
            assert r["relevance_score"] >= 0.30

        print(f"[PASS] Minimum threshold verified: strict filter gave 0, normal filter gave {len(normal_result['results'])}.")
    finally:
        db.close()


def test_postgresql_audit_logging():
    """
    Test 3: Verify Alert and MitigationResult records are stored in PostgreSQL.
    """
    print("\n--- Test 3: PostgreSQL Audit Logging (Alert & MitigationResult) ---")
    db = SessionLocal()
    try:
        service = get_mitigation_service()
        alert_text = "Audit Test: Ransomware activity detected on file cluster."
        result = service.search_mitigations(
            alert=alert_text,
            top_k=2,
            min_threshold=0.30,
            severity="critical",
            save_record=True,
            db=db,
        )

        assert result["alert_id"] is not None
        alert_id = result["alert_id"]

        # Verify Alert in DB
        db_alert = db.query(Alert).filter(Alert.id == alert_id).first()
        assert db_alert is not None
        assert db_alert.description == alert_text
        assert db_alert.severity == "critical"

        # Verify MitigationResult in DB
        mitigations = db.query(MitigationResult).filter(MitigationResult.alert_id == alert_id).all()
        assert len(mitigations) == len(result["results"])
        for m in mitigations:
            assert m.document_id is not None
            assert m.chunk_id is not None
            assert len(m.mitigation_text) > 0
            assert m.relevance_score > 0

        print(f"[PASS] Stored Alert ID {alert_id} with {len(mitigations)} MitigationResult rows in PostgreSQL.")
    finally:
        db.close()


def test_api_endpoint_validation():
    """
    Test 4: Verify API validation for POST /api/mitigation/search.
    """
    print("\n--- Test 4: API Endpoint Validation (POST /api/mitigation/search) ---")
    login_resp = client.post("/api/auth/login", json={"email": "analyst@cybershield.io", "password": "AnalystPass123!"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Empty alert string
    resp = client.post("/api/mitigation/search", json={"alert": ""}, headers=headers)
    assert resp.status_code == 400
    assert "cannot be empty" in resp.json()["detail"].lower()

    # 2. Whitespace alert string
    resp = client.post("/api/mitigation/search", json={"alert": "    "}, headers=headers)
    assert resp.status_code == 400
    assert "cannot be empty" in resp.json()["detail"].lower()

    # 3. Invalid top_k (< 1)
    resp = client.post("/api/mitigation/search", json={"alert": "ransomware", "top_k": 0}, headers=headers)
    assert resp.status_code == 400
    assert "top_k" in resp.json()["detail"].lower()

    # 4. Invalid top_k (> 100)
    resp = client.post("/api/mitigation/search", json={"alert": "ransomware", "top_k": 101}, headers=headers)
    assert resp.status_code == 400
    assert "top_k" in resp.json()["detail"].lower()

    # 5. Invalid min_threshold (< 0.0 or > 1.0)
    resp = client.post("/api/mitigation/search", json={"alert": "ransomware", "min_threshold": 1.5}, headers=headers)
    assert resp.status_code == 400
    assert "min_threshold" in resp.json()["detail"].lower()

    print("[PASS] All API validation checks rejected bad input with 400 Bad Request.")


def test_three_sample_security_alerts():
    """
    Test 5: Benchmark 3 sample security alerts and verify source document evidence:
    - Alert 1: "Multiple Windows endpoints are showing suspicious PowerShell activity."
    - Alert 2: "Ransomware encryption spreading across network drives."
    - Alert 3: "SQL injection vulnerability identified in web authentication endpoint."
    """
    print("\n--- Test 5: Benchmark 3 Sample Security Alerts & Verify Sources ---")
    login_resp = client.post("/api/auth/login", json={"email": "analyst@cybershield.io", "password": "AnalystPass123!"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    sample_alerts = [
        {
            "alert": "Multiple Windows endpoints are showing suspicious PowerShell activity.",
            "expected_keyword": "powershell",
            "expected_doc_type": "incident_runbook",
        },
        {
            "alert": "Ransomware encryption spreading across network drives.",
            "expected_keyword": "ransomware",
            "expected_doc_type": "incident_runbook",
        },
        {
            "alert": "SQL injection vulnerability identified in web authentication endpoint.",
            "expected_keyword": "sql",
            "expected_doc_type": "vulnerability_advisory",
        },
    ]

    for item in sample_alerts:
        alert_text = item["alert"]
        resp = client.post(
            "/api/mitigation/search",
            json={"alert": alert_text, "top_k": 3, "min_threshold": 0.35},
            headers=headers,
        )
        assert resp.status_code == 200, f"Failed for alert: {alert_text} - {resp.text}"
        data = resp.json()

        assert data["alert"] == alert_text
        assert len(data["results"]) > 0, f"Expected results for: {alert_text}"

        top_match = data["results"][0]
        print(f"\nAlert: '{alert_text}'")
        print(f"  Source Document Title : {top_match['document_title']}")
        print(f"  Source Document Type  : {top_match['document_type']}")
        print(f"  Source Document ID    : {top_match['document_id']}")
        print(f"  Source Chunk ID       : {top_match['chunk_id']}")
        print(f"  Relevance Score       : {top_match['relevance_score']:.4f}")
        print(f"  Mitigation Steps      : {top_match['mitigation_text'][:120]}...")

        # Verify evidence is from source document
        assert top_match["document_title"] is not None
        assert top_match["document_type"] == item["expected_doc_type"]
        assert item["expected_keyword"] in top_match["mitigation_text"].lower()
        assert top_match["relevance_score"] >= 0.60

    print("\n[PASS] All 3 benchmark security alerts retrieved authentic mitigations from source documents.")


def run_all_day7_tests():
    print("=" * 70)
    print("   CYBERSHIELD DAY 7 - MITIGATION RETRIEVAL API TEST SUITE      ")
    print("=" * 70)

    Base.metadata.create_all(bind=engine)
    test_mitigation_service_unit()
    test_minimum_relevance_threshold()
    test_postgresql_audit_logging()
    test_api_endpoint_validation()
    test_three_sample_security_alerts()

    print("\n" + "=" * 70)
    print("   ALL DAY 7 MITIGATION RETRIEVAL API TESTS PASSED!             ")
    print("=" * 70)


if __name__ == "__main__":
    run_all_day7_tests()
