# CyberShield Backend Service

CyberShield is a cybersecurity mitigation retrieval platform designed to allow security analysts to rapidly query threat intelligence, incident runbooks, and vulnerability advisories to retrieve exact mitigation steps during active security alerts.

## Requirements & Setup

### Prerequisites
- Python 3.10+
- PostgreSQL database server (v12+)

### Environment Setup
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Configure database connection parameters in `.env`:
   ```env
   DB_HOST=localhost
   DB_PORT=5432
   DB_USER=postgres
   DB_PASSWORD=postgres_password
   DB_NAME=cybershield_db
   DATABASE_URL=postgresql://postgres:postgres_password@localhost:5432/cybershield_db
   ```

### Virtual Environment & Dependencies
1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## Database Configuration & Initialization

### Initialize Database Tables
To create all database tables (`users`, `documents`, `document_chunks`, `alerts`, `mitigation_results`), execute:
```bash
python -m app.init_db
```

### Test Database Connection
To verify PostgreSQL connection and test schema creation:
```bash
python -m app.test_db
```

---

## Running the Backend Application

Start the FastAPI development server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API Base URL: `http://localhost:8000`
- API Health Check: `http://localhost:8000/api/v1/health`
- Interactive Swagger OpenAPI Docs: `http://localhost:8000/docs`

---

## Database Models Architecture

The core entities defined in SQLAlchemy (`app/models.py`):

1. **User** (`users`): Represents system users and analysts.
2. **Document** (`documents`): Stores threat intelligence, incident runbooks, and vulnerability advisories.
   - `document_type` values: `threat_intelligence`, `incident_runbook`, `vulnerability_advisory`
3. **DocumentChunk** (`document_chunks`): Stores partitioned text sections of documents.
4. **Alert** (`alerts`): Security alerts requiring mitigation lookup.
5. **MitigationResult** (`mitigation_results`): Maps security alerts to relevant document chunks and scores.

---

## Semantic Vector Search (FAISS) - Day 6

CyberShield uses **FAISS** (Facebook AI Similarity Search) and **Sentence Transformers** (`all-MiniLM-L6-v2`) to perform dense vector similarity search across document chunks.

### Endpoints
- **Search Document Chunks**:
  ```http
  GET /api/search?q=<query>&top_k=5
  ```
  Query parameters:
  - `q`: Security alert description or query (required, non-empty)
  - `top_k`: Number of top matching chunks to retrieve (1-100, default: 5)

- **Rebuild FAISS Index**:
  ```http
  POST /api/search/rebuild?auto_embed=true
  ```

### Example Search Response
```json
[
  {
    "chunk_id": 18,
    "document_id": 11,
    "document_title": "Endpoint Isolation and Incident Response Runbook",
    "chunk_content": "Incident Response Runbook: Endpoint Isolation and Host Remediation...",
    "content": "Incident Response Runbook: Endpoint Isolation and Host Remediation...",
    "similarity_score": 0.735,
    "relevance_score": 0.735
  }
]
```

### Running Vector Search Tests
```bash
python app/test_vector_search.py
```

---

## Cybersecurity Mitigation Retrieval API - Day 7

CyberShield provides a mitigation retrieval pipeline (`POST /api/mitigation/search`) that translates active security alerts into verbatim mitigation steps extracted from ingested incident runbooks, threat intelligence reports, and vulnerability advisories.

### Endpoint
```http
POST /api/mitigation/search
Content-Type: application/json

{
  "alert": "Multiple Windows endpoints are showing suspicious PowerShell activity.",
  "top_k": 5,
  "min_threshold": 0.30
}
```

### Response Structure
```json
{
  "alert": "Multiple Windows endpoints are showing suspicious PowerShell activity.",
  "results": [
    {
      "document_id": 14,
      "document_title": "PowerShell Threat Intelligence and Incident Runbook",
      "document_type": "incident_runbook",
      "chunk_id": 22,
      "mitigation_text": "Incident Runbook: Suspicious PowerShell Activity and Host Containment. When multiple Windows endpoints show suspicious PowerShell execution...",
      "relevance_score": 0.8142,
      "source_file": "powershell_incident_runbook.txt"
    }
  ],
  "total_results": 1,
  "alert_id": 4
}
```

### Running Mitigation Retrieval Tests
```bash
python app/test_mitigation.py
```

---

## Grounded AI Mitigation Response (RAG) - Day 8

CyberShield integrates an AI response layer on top of semantic retrieval (`POST /api/mitigation/answer`).
- Retrieval is the sole source of truth (grounded synthesis, zero hallucination).
- Summarizes actionable mitigation steps strictly from retrieved chunks.
- Cites source documents and returns retrieval sources alongside the answer.
- Returns `"Insufficient information found in the available security documents."` when no relevant context is found.

### Endpoint
```http
POST /api/mitigation/answer
Content-Type: application/json

{
  "alert": "Multiple Windows endpoints are showing suspicious PowerShell activity."
}
```

### Response Structure
```json
{
  "alert": "Multiple Windows endpoints are showing suspicious PowerShell activity.",
  "answer": "Based on the available security documentation, the following mitigation steps are recommended for this alert:\n\n**Source: PowerShell Threat Intelligence and Incident Runbook (Incident Runbook)**\n- Immediately isolate affected Windows endpoints via host-based firewall or EDR containment.\n- Terminate rogue PowerShell process trees (powershell.exe, pwsh.exe) and parent processes.\n- Enable PowerShell Script Block Logging (Event ID 4104) and Module Logging across Group Policy.\n- Enforce PowerShell Constrained Language Mode and configure AppLocker / WDAC policies.\n- Revoke compromised user credentials and invalidate Kerberos golden tickets.",
  "sources": [
    {
      "document_id": 16,
      "document_title": "PowerShell Threat Intelligence and Incident Runbook",
      "document_type": "incident_runbook",
      "chunk_id": 22,
      "mitigation_text": "Incident Runbook: Suspicious PowerShell Activity and Host Containment...",
      "relevance_score": 0.7979,
      "source_file": "powershell_incident_runbook.txt"
    }
  ]
}
```

### Running RAG Tests
```bash
python app/test_rag.py
```

---

## Authentication & Security (RBAC) - Day 9

CyberShield backend is protected with **JWT (JSON Web Token) authentication** and **Bcrypt password hashing**, enforcing **Role-Based Access Control (RBAC)** across administrative operations and security analyst workflows.

### Default Test Credentials
The backend automatically seeds default system accounts upon initial startup:
| Role | Email | Password | Permissions |
|------|-------|----------|-------------|
| **Admin** | `admin@cybershield.io` | `AdminPass123!` | Upload documents, chunk & embed, rebuild FAISS index, create users, search & view |
| **Analyst** | `analyst@cybershield.io` | `AnalystPass123!` | Semantic search, mitigation retrieval, grounded AI answers, view documents |

### Authentication Endpoints

#### 1. User Login
```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "analyst@cybershield.io",
  "password": "AnalystPass123!"
}
```
**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 3,
    "name": "Security Analyst",
    "email": "analyst@cybershield.io",
    "role": "analyst",
    "created_at": "2026-09-29T12:00:00Z"
  }
}
```

#### 2. User Registration
```http
POST /api/auth/register
Content-Type: application/json

{
  "name": "Jane Doe",
  "email": "jane.doe@cybershield.io",
  "password": "SecurePassword123!",
  "role": "analyst"
}
```
**Response (201 Created):**
```json
{
  "id": 4,
  "name": "Jane Doe",
  "email": "jane.doe@cybershield.io",
  "role": "analyst",
  "created_at": "2026-09-29T12:05:00Z"
}
```

#### 3. Admin User Creation (Admin only)
```http
POST /api/auth/users
Authorization: Bearer <ADMIN_JWT_TOKEN>
Content-Type: application/json

{
  "name": "New Analyst",
  "email": "analyst2@cybershield.io",
  "password": "Password123!",
  "role": "analyst"
}
```

#### 4. Current User Profile
```http
GET /api/auth/me
Authorization: Bearer <JWT_TOKEN>
```

### Role-Based Access Control (RBAC) Matrix

| Endpoint | Method | Required Role | Description |
|----------|--------|---------------|-------------|
| `/api/auth/login` | POST | Public | Authenticate and obtain JWT |
| `/api/auth/register` | POST | Public | Register new analyst account |
| `/api/auth/me` | GET | Authenticated | Get current user profile |
| `/api/auth/users` | POST | `admin` | Admin creation of new users |
| `/api/documents/upload` | POST | `admin` | Upload and extract threat docs (.pdf, .docx, .txt) |
| `/api/documents/{id}/process` | POST | `admin` | Chunk document content |
| `/api/documents/{id}/embed` | POST | `admin` | Generate vector embeddings |
| `/api/documents` | GET | Authenticated | List stored security documents |
| `/api/documents/{id}` | GET | Authenticated | Get document details |
| `/api/documents/{id}/chunks` | GET | Authenticated | Get chunks for document |
| `/api/search` | GET | Authenticated | Semantic vector search |
| `/api/search/rebuild` | POST | `admin` | Rebuild FAISS index from stored embeddings |
| `/api/mitigation/search` | POST | Authenticated | Retrieve structured mitigation steps |
| `/api/mitigation/answer` | POST | Authenticated | Grounded AI RAG answer generation |

### Security Checks & Safeguards
- **Zero Credential Leaks**: Password hashes (`password_hash`) are strictly excluded from all Pydantic response models (`UserResponse`, `TokenResponse`, etc.).
- **Upload Validation**: Enforces maximum file size limit (20MB) and strict allowlist for supported cybersecurity document extensions (`.pdf`, `.docx`, `.txt`).
- **Input Validation**: Request bodies and query parameters (`top_k`, `min_threshold`, `alert`, `q`) are validated with strict bounds and non-empty checks.
- **Centralized Error Handling**: Standardized structured JSON responses for `400 Bad Request`, `401 Unauthorized`, `403 Forbidden`, `404 Not Found`, `422 Unprocessable Entity`, and `500 Internal Server Error`.

### Running Day 9 Security & Integration Tests
```bash
# Run pytest across the Day 9 test suite
pytest app/test_day9_auth_security.py -v

# Or run directly via Python
python app/test_day9_auth_security.py
```

