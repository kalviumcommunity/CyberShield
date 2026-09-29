"""
Day 9 Automated Test Suite: Authentication, Security, RBAC, and Full Flow Integration.

Tests:
1. Login with valid credentials (admin and analyst)
2. Login with invalid credentials (wrong password, non-existent user)
3. Registration flow & admin user creation
4. Protected endpoints rejection without token (401)
5. Role-based access control (RBAC): analyst blocked from admin endpoints (403)
6. Security checks:
   - Password hashes never exposed
   - Upload file type & size validation
   - Request data validation
7. Complete end-to-end backend flow:
   Login -> Upload -> Process -> Embed -> Search -> Retrieve Mitigation -> Grounded RAG Answer -> No-result Fallback
"""

import io
import os
import sys
import pytest
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import User
from app.services.auth_service import init_default_users
from app.services.rag_service import INSUFFICIENT_INFO_MESSAGE

client = TestClient(app)


def setup_module():
    """Ensure database tables and default users exist."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        init_default_users(db)


def get_token(email: str, password: str) -> str:
    """Helper to authenticate and return bearer JWT access token."""
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return resp.json()["access_token"]


def get_auth_headers(email: str, password: str) -> dict:
    """Helper to return Authorization headers with JWT token."""
    token = get_token(email, password)
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# 1. Login Tests
# ---------------------------------------------------------------------------

def test_login_success_admin():
    """Verify administrator login returns valid JWT token and user profile."""
    resp = client.post(
        "/api/auth/login",
        json={"email": "admin@cybershield.io", "password": "AdminPass123!"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"].lower() == "bearer"
    assert data["user"]["email"] == "admin@cybershield.io"
    assert data["user"]["role"] == "admin"
    # Security check: password hash must NEVER be exposed
    assert "password_hash" not in data["user"]
    assert "password" not in data["user"]


def test_login_success_analyst():
    """Verify security analyst login returns valid JWT token and user profile."""
    resp = client.post(
        "/api/auth/login",
        json={"email": "analyst@cybershield.io", "password": "AnalystPass123!"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == "analyst@cybershield.io"
    assert data["user"]["role"] == "analyst"
    assert "password_hash" not in data["user"]


def test_login_invalid_password():
    """Verify login with incorrect password returns 401 Unauthorized."""
    resp = client.post(
        "/api/auth/login",
        json={"email": "admin@cybershield.io", "password": "WrongPassword999!"},
    )
    assert resp.status_code == 401
    assert "incorrect" in resp.json()["detail"].lower()


def test_login_nonexistent_user():
    """Verify login with unregistered email returns 401 Unauthorized."""
    resp = client.post(
        "/api/auth/login",
        json={"email": "ghost.user@cybershield.io", "password": "SomePassword123!"},
    )
    assert resp.status_code == 401
    assert "incorrect" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 2. Registration & User Management
# ---------------------------------------------------------------------------

def test_registration_and_duplicate_check():
    """Verify public user registration and duplicate prevention."""
    unique_email = f"test.analyst.{os.urandom(4).hex()}@cybershield.io"
    payload = {
        "name": "Test Onboard Analyst",
        "email": unique_email,
        "password": "SecurePassword123!",
        "role": "analyst",
    }
    # Successful registration
    reg_resp = client.post("/api/auth/register", json=payload)
    assert reg_resp.status_code == 201
    reg_data = reg_resp.json()
    assert reg_data["email"] == unique_email
    assert reg_data["role"] == "analyst"
    assert "password_hash" not in reg_data

    # Duplicate registration check
    dup_resp = client.post("/api/auth/register", json=payload)
    assert dup_resp.status_code == 400
    assert "already exists" in dup_resp.json()["detail"].lower()


def test_admin_user_creation_and_analyst_forbidden():
    """Verify only admins can invoke the admin user creation endpoint."""
    admin_headers = get_auth_headers("admin@cybershield.io", "AdminPass123!")
    analyst_headers = get_auth_headers("analyst@cybershield.io", "AnalystPass123!")

    new_user_data = {
        "name": "Admin Created Analyst",
        "email": f"created.{os.urandom(4).hex()}@cybershield.io",
        "password": "CreatedPass123!",
        "role": "analyst",
    }

    # Analyst trying to create user -> 403 Forbidden
    forbidden_resp = client.post("/api/auth/users", json=new_user_data, headers=analyst_headers)
    assert forbidden_resp.status_code == 403

    # Admin creating user -> 201 Created
    created_resp = client.post("/api/auth/users", json=new_user_data, headers=admin_headers)
    assert created_resp.status_code == 201
    assert created_resp.json()["email"] == new_user_data["email"]


def test_get_current_user_profile():
    """Verify GET /api/auth/me returns the authenticated user profile."""
    analyst_headers = get_auth_headers("analyst@cybershield.io", "AnalystPass123!")
    resp = client.get("/api/auth/me", headers=analyst_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "analyst@cybershield.io"
    assert data["role"] == "analyst"
    assert "password_hash" not in data


# ---------------------------------------------------------------------------
# 3. Protected Endpoints Rejection Tests (401 Unauthorized)
# ---------------------------------------------------------------------------

def test_protected_endpoints_without_auth():
    """Verify protected endpoints reject requests lacking authentication."""
    endpoints = [
        ("GET", "/api/documents"),
        ("GET", "/api/documents/1"),
        ("GET", "/api/documents/1/chunks"),
        ("POST", "/api/documents/upload"),
        ("POST", "/api/documents/1/process"),
        ("POST", "/api/documents/1/embed"),
        ("GET", "/api/search?q=test"),
        ("POST", "/api/search/rebuild"),
        ("POST", "/api/mitigation/search"),
        ("POST", "/api/mitigation/answer"),
        ("GET", "/api/auth/me"),
    ]
    for method, path in endpoints:
        if method == "GET":
            resp = client.get(path)
        else:
            resp = client.post(path)
        assert resp.status_code == 401, f"{method} {path} returned {resp.status_code}, expected 401"
        assert "detail" in resp.json()


def test_protected_endpoint_invalid_token():
    """Verify requests with malformed/forged tokens return 401 Unauthorized."""
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.jwt.token"})
    assert resp.status_code == 401
    assert "invalid" in resp.json()["detail"].lower() or "expired" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 4. Role-Based Access Control (RBAC) Enforcement (403 Forbidden)
# ---------------------------------------------------------------------------

def test_analyst_cannot_upload_document():
    """Analysts should NOT be able to upload documents (admin only)."""
    analyst_headers = get_auth_headers("analyst@cybershield.io", "AnalystPass123!")
    fake_file = io.BytesIO(b"Unauthorized document upload content")
    resp = client.post(
        "/api/documents/upload",
        files={"file": ("unauthorized.txt", fake_file, "text/plain")},
        data={"document_type": "incident_runbook"},
        headers=analyst_headers,
    )
    assert resp.status_code == 403, f"Expected 403 Forbidden, got {resp.status_code}: {resp.text}"
    assert "access denied" in resp.json()["detail"].lower()


def test_analyst_cannot_process_document():
    """Analysts should NOT be able to trigger document chunking."""
    analyst_headers = get_auth_headers("analyst@cybershield.io", "AnalystPass123!")
    resp = client.post("/api/documents/1/process", headers=analyst_headers)
    assert resp.status_code == 403


def test_analyst_cannot_embed_document():
    """Analysts should NOT be able to trigger document embedding."""
    analyst_headers = get_auth_headers("analyst@cybershield.io", "AnalystPass123!")
    resp = client.post("/api/documents/1/embed", headers=analyst_headers)
    assert resp.status_code == 403


def test_analyst_cannot_rebuild_search_index():
    """Analysts should NOT be able to rebuild the FAISS search index."""
    analyst_headers = get_auth_headers("analyst@cybershield.io", "AnalystPass123!")
    resp = client.post("/api/search/rebuild", headers=analyst_headers)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 5. Security & Input Validation Checks
# ---------------------------------------------------------------------------

def test_upload_validation_unsupported_file_extension():
    """Verify file upload rejects dangerous or unsupported extensions (e.g. .exe)."""
    admin_headers = get_auth_headers("admin@cybershield.io", "AdminPass123!")
    fake_exe = io.BytesIO(b"MZ\x90\x00BinaryData")
    resp = client.post(
        "/api/documents/upload",
        files={"file": ("malware.exe", fake_exe, "application/octet-stream")},
        data={"document_type": "threat_intelligence"},
        headers=admin_headers,
    )
    assert resp.status_code == 400
    assert "unsupported file type" in resp.json()["detail"].lower()


def test_upload_validation_empty_filename():
    """Verify file upload rejects empty filename."""
    admin_headers = get_auth_headers("admin@cybershield.io", "AdminPass123!")
    fake_file = io.BytesIO(b"Valid content")
    resp = client.post(
        "/api/documents/upload",
        files={"file": ("", fake_file, "text/plain")},
        data={"document_type": "incident_runbook"},
        headers=admin_headers,
    )
    assert resp.status_code in (400, 422)


def test_mitigation_search_validation():
    """Verify input validation on mitigation search endpoint."""
    analyst_headers = get_auth_headers("analyst@cybershield.io", "AnalystPass123!")

    # Empty alert
    resp = client.post("/api/mitigation/search", json={"alert": ""}, headers=analyst_headers)
    assert resp.status_code == 400

    # Invalid top_k
    resp = client.post("/api/mitigation/search", json={"alert": "ransomware", "top_k": 0}, headers=analyst_headers)
    assert resp.status_code == 400

    # Invalid min_threshold
    resp = client.post("/api/mitigation/search", json={"alert": "ransomware", "min_threshold": 2.5}, headers=analyst_headers)
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# 6. Complete End-to-End Backend Flow Test
# ---------------------------------------------------------------------------

def test_complete_backend_security_flow():
    """
    Test the complete, secure end-to-end backend workflow:
    1. Admin Login
    2. Admin Uploads Security Document
    3. Admin Processes Document into Chunks
    4. Admin Generates Vector Embeddings
    5. Analyst Login
    6. Analyst Performs Semantic FAISS Search
    7. Analyst Retrieves Mitigations
    8. Analyst Generates Grounded AI Mitigation Answer
    9. Analyst Tests No-Result Fallback
    """
    print("\n[FLOW] 1. Admin Login")
    admin_headers = get_auth_headers("admin@cybershield.io", "AdminPass123!")
    assert "Authorization" in admin_headers

    print("[FLOW] 2. Admin Uploads Security Document")
    sample_content = (
        "Active Incident Runbook: Cobalt Strike Beacon Detection and Remediation. "
        "When Cobalt Strike beacon activity or suspicious malleable C2 traffic is detected: "
        "1. Isolate the compromised host immediately from the local network segment. "
        "2. Kill memory-injected processes and dump process memory for forensic analysis. "
        "3. Block known Cobalt Strike external command-and-control IP addresses and domains at the perimeter firewall. "
        "4. Force enterprise-wide password resets for all accounts authenticated to the host. "
        "5. Scan domain controllers for pass-the-hash and silver ticket compromise."
    )
    file_bytes = io.BytesIO(sample_content.encode("utf-8"))
    upload_resp = client.post(
        "/api/documents/upload",
        files={"file": ("cobalt_strike_runbook.txt", file_bytes, "text/plain")},
        data={
            "document_type": "incident_runbook",
            "title": "Cobalt Strike Beacon Detection and Remediation",
        },
        headers=admin_headers,
    )
    assert upload_resp.status_code == 201, f"Upload failed: {upload_resp.text}"
    doc_data = upload_resp.json()
    doc_id = doc_data["id"]
    assert doc_id is not None
    assert doc_data["uploaded_by"] is not None

    print(f"[FLOW] 3. Admin Processes Document into Chunks (doc_id={doc_id})")
    process_resp = client.post(f"/api/documents/{doc_id}/process", headers=admin_headers)
    assert process_resp.status_code == 200, f"Process failed: {process_resp.text}"
    process_data = process_resp.json()
    assert process_data["chunks_created"] > 0

    print(f"[FLOW] 4. Admin Generates Vector Embeddings (doc_id={doc_id})")
    embed_resp = client.post(f"/api/documents/{doc_id}/embed", headers=admin_headers)
    assert embed_resp.status_code == 200, f"Embed failed: {embed_resp.text}"
    embed_data = embed_resp.json()
    assert embed_data["chunks_embedded"] > 0
    assert embed_data["embedding_dimension"] == 384

    print("[FLOW] 5. Analyst Login")
    analyst_headers = get_auth_headers("analyst@cybershield.io", "AnalystPass123!")
    assert "Authorization" in analyst_headers

    print("[FLOW] 6. Analyst Performs Semantic FAISS Search")
    search_resp = client.get(
        "/api/search?q=Cobalt Strike beacon detected on internal workstation&top_k=3",
        headers=analyst_headers,
    )
    assert search_resp.status_code == 200, f"Search failed: {search_resp.text}"
    search_results = search_resp.json()
    assert len(search_results) > 0
    assert any("cobalt strike" in r["document_title"].lower() or "cobalt strike" in r["chunk_content"].lower() for r in search_results)
    top_score = search_results[0]["similarity_score"]
    assert top_score > 0.40

    print("[FLOW] 7. Analyst Retrieves Structured Mitigations")
    mitigation_resp = client.post(
        "/api/mitigation/search",
        json={
            "alert": "Cobalt Strike beacon activity detected with suspicious outbound C2 traffic.",
            "top_k": 3,
            "min_threshold": 0.30,
        },
        headers=analyst_headers,
    )
    assert mitigation_resp.status_code == 200, f"Mitigation search failed: {mitigation_resp.text}"
    mitigation_data = mitigation_resp.json()
    assert len(mitigation_data["results"]) > 0
    top_mitigation = mitigation_data["results"][0]
    assert "relevance_score" in top_mitigation
    assert "mitigation_text" in top_mitigation
    assert top_mitigation["relevance_score"] >= 0.30

    print("[FLOW] 8. Analyst Generates Grounded AI Mitigation Answer")
    answer_resp = client.post(
        "/api/mitigation/answer",
        json={
            "alert": "Cobalt Strike beacon activity detected with suspicious outbound C2 traffic.",
            "top_k": 3,
            "min_threshold": 0.30,
        },
        headers=analyst_headers,
    )
    assert answer_resp.status_code == 200, f"Answer generation failed: {answer_resp.text}"
    answer_data = answer_resp.json()
    assert "answer" in answer_data
    assert len(answer_data["sources"]) > 0
    assert answer_data["answer"] != INSUFFICIENT_INFO_MESSAGE
    print(f"       Grounded answer snippet: {answer_data['answer'][:120]}...")

    print("[FLOW] 9. Analyst Tests No-Result Fallback Case")
    no_result_resp = client.post(
        "/api/mitigation/answer",
        json={
            "alert": "What are the rules of professional cricket and baseball?",
            "top_k": 3,
            "min_threshold": 0.65,
        },
        headers=analyst_headers,
    )
    assert no_result_resp.status_code == 200
    no_result_data = no_result_resp.json()
    assert no_result_data["answer"] == INSUFFICIENT_INFO_MESSAGE
    assert len(no_result_data["sources"]) == 0
    print("       Fallback message verified successfully.")


if __name__ == "__main__":
    setup_module()
    print("Running Day 9 Authentication and Security Test Suite...")
    test_login_success_admin()
    test_login_success_analyst()
    test_login_invalid_password()
    test_login_nonexistent_user()
    test_registration_and_duplicate_check()
    test_admin_user_creation_and_analyst_forbidden()
    test_get_current_user_profile()
    test_protected_endpoints_without_auth()
    test_protected_endpoint_invalid_token()
    test_analyst_cannot_upload_document()
    test_analyst_cannot_process_document()
    test_analyst_cannot_embed_document()
    test_analyst_cannot_rebuild_search_index()
    test_upload_validation_unsupported_file_extension()
    test_upload_validation_empty_filename()
    test_mitigation_search_validation()
    test_complete_backend_security_flow()
    print("\n" + "=" * 70)
    print("ALL DAY 9 AUTH, SECURITY, AND FLOW TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)
