# CyberShield — Cybersecurity Threat Intelligence & Mitigation Platform

CyberShield is a production-grade cybersecurity mitigation retrieval platform. It enables Security Operations Center (SOC) analysts to rapidly input active security alerts and retrieve verbatim, validated mitigation steps from ingested incident runbooks, threat intelligence reports, and vulnerability advisories using semantic vector search and grounded retrieval-augmented generation (RAG).

---

## Complete Architecture

```text
React Frontend (Vite / Next.js)
        ↓  (Bearer JWT + JSON / Multipart)
FastAPI Backend (REST API / Async ASGI)
        ↓
JWT Authentication & Role-Based Access Control (Admin / Analyst)
        ↓
Document Management (PDF, DOCX, TXT Upload & Storage)
        ↓
Text Extraction (PyMuPDF / python-docx / utf-8)
        ↓
Text Chunking (500–800 words with 60-word overlap)
        ↓
Embeddings (Sentence Transformers: all-MiniLM-L6-v2, 384-d)
        ↓
FAISS Vector Index (IndexFlatIP Cosine Similarity)
        ↓
Semantic Retrieval (Descending relevance scoring with thresholds)
        ↓
Mitigation Results (Incident Auditing stored in PostgreSQL)
        ↓
Grounded AI Response (Strictly grounded synthesis with zero hallucination)
```

---

## Tech Stack

| Component | Technology | Description |
|-----------|------------|-------------|
| **Framework** | FastAPI 0.110+ | High-performance Python ASGI web framework |
| **Server** | Uvicorn 0.28+ | Lightning-fast ASGI production web server |
| **Database** | PostgreSQL 15+ & SQLAlchemy 2.0 | Relational database with pooled connections & ORM |
| **Vector Index** | FAISS (faiss-cpu 1.8+) | Facebook AI Similarity Search with Inner Product / Cosine similarity |
| **Embeddings** | Sentence Transformers (`all-MiniLM-L6-v2`) | 384-dimensional dense semantic representations |
| **Text Parsers** | PyMuPDF (`fitz`), `python-docx` | Native binary extraction for PDF, DOCX, and TXT |
| **Authentication** | PyJWT & Bcrypt | Stateless JWT bearer tokens with cryptographically salted hashing |
| **Validation** | Pydantic v2 & Pydantic-Settings | Strict schema validation, typed payloads, and env parsing |
| **Testing** | Pytest 8.0+ & HTTPX TestClient | Automated test suites covering all integration pipelines |
| **Deployment** | Docker, Docker Compose, Render, Railway | Containerized with cloud platform blueprints |

---

## Repository Structure

```text
CyberShield/
├── README.md                                  # Complete project documentation & API guide
├── docker-compose.yml                         # Full-stack Docker orchestration (FastAPI + PostgreSQL)
├── .gitignore                                 # Root Git exclusions (secrets, env, caches, uploads)
└── backend/                                   # FastAPI backend service
    ├── .env.example                           # Example environment template
    ├── .gitignore                             # Backend Git exclusions
    ├── Dockerfile                             # Multi-stage production container build
    ├── Procfile                               # Process file for Render, Railway, and Heroku
    ├── railway.json                           # Railway deployment configuration
    ├── render.yaml                            # Render Infrastructure-as-Code Blueprint
    ├── requirements.txt                       # Locked dependencies
    ├── README.md                              # Backend local documentation
    ├── uploads/                               # Local document storage directory (git-ignored)
    └── app/
        ├── config.py                          # Pydantic BaseSettings & DB URL normalizer
        ├── database.py                        # SQLAlchemy engine with pre-ping pooling
        ├── init_db.py                         # Database schema generator
        ├── main.py                            # FastAPI app, CORS, error handlers & routers
        ├── test_day10_e2e_integration.py      # Day 10 full end-to-end integration test suite
        ├── test_day9_auth_security.py         # Day 9 auth, RBAC, and security test suite
        ├── test_rag.py                        # Day 8 grounded RAG AI answer tests
        ├── test_mitigation.py                 # Day 7 cybersecurity mitigation tests
        ├── test_vector_search.py              # Day 6 FAISS vector search tests
        ├── test_embeddings.py                 # Day 5 vector embedding tests
        ├── test_chunking.py                   # Day 4 text chunking tests
        ├── test_documents.py                  # Day 3 multi-format upload & extraction tests
        ├── test_db.py                         # PostgreSQL connectivity tests
        ├── dependencies/                      # Route guards & RBAC dependencies
        ├── models/                            # SQLAlchemy 2.0 ORM models
        ├── routes/                            # FastAPI route modules (auth, docs, search, mitigation, health)
        ├── schemas/                           # Pydantic v2 schemas
        └── services/                          # Core business logic (RAG, FAISS, embeddings, chunking)
```

---

## Requirements & Setup

### Prerequisites
- Python 3.10+ (tested on Python 3.11, 3.12, 3.14)
- PostgreSQL database server (v12 or newer)
- Git

### 1. Environment Configuration
Copy `.env.example` to `.env` in the `backend/` directory:
```bash
cp backend/.env.example backend/.env
```

Configure your environment variables:
```env
# Application Configuration
APP_NAME="CyberShield Threat Intelligence API"
APP_ENV="development"
DEBUG=True
HOST="0.0.0.0"
PORT=8000

# CORS Allowed Origins (Comma-separated or wildcard '*')
ALLOWED_ORIGINS="http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"

# JWT Authentication Configuration
JWT_SECRET_KEY="replace_with_a_secure_random_key_in_production"
JWT_ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# PostgreSQL Database Configuration
DB_HOST="localhost"
DB_PORT=5432
DB_USER="postgres"
DB_PASSWORD="postgres_password"
DB_NAME="cybershield_db"
DATABASE_URL="postgresql://postgres:postgres_password@localhost:5432/cybershield_db"
```

> **Security Note**: Never commit `.env` to version control. Keep secrets strictly in environment variables.

---

### 2. Virtual Environment & Dependencies

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux / macOS:
source venv/bin/activate

# Install all required dependencies
pip install -r requirements.txt
```

---

### 3. Database Setup & Initialization

Ensure your PostgreSQL service is running and create the database:
```sql
CREATE DATABASE cybershield_db;
```

Initialize all tables and relationships:
```bash
python -m app.init_db
```

Verify connection:
```bash
python -m app.test_db
```

Default user credentials automatically seeded upon startup:
| Role | Email | Password | Access Rights |
|------|-------|----------|---------------|
| **Admin** | `admin@cybershield.io` | `AdminPass123!` | Upload documents, chunk, embed, rebuild index, manage users |
| **Analyst** | `analyst@cybershield.io` | `AnalystPass123!` | Query semantic search, retrieve mitigations, generate RAG answers |

---

## How to Run the Backend

### Development Mode (with hot-reload)
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

### Access URLs
- **API Base URL**: `http://localhost:8000`
- **Health Check**: `http://localhost:8000/api/health`
- **Interactive Swagger Docs**: `http://localhost:8000/docs`
- **ReDoc Documentation**: `http://localhost:8000/redoc`

---

## Docker & Docker Compose Setup

Run both the PostgreSQL database and FastAPI backend in Docker:
```bash
# From repository root
docker compose up --build -d
```

Verify services:
```bash
docker compose ps
curl http://localhost:8000/api/health
```

Stop services:
```bash
docker compose down
```

---

## All API Endpoints Reference

### 1. Health & Discovery

#### `GET /api/health`
Operational readiness check verifying FastAPI status, PostgreSQL connectivity, and FAISS vector index status.
- **Auth**: Public
- **Response (200 OK)**:
```json
{
  "status": "healthy",
  "app": "CyberShield Threat Intelligence API",
  "version": "1.0.0",
  "environment": "development",
  "database": "connected",
  "vector_index": {
    "status": "ready",
    "indexed_chunks": 31
  },
  "timestamp": "2026-09-30T05:19:23.618000+00:00",
  "message": "CyberShield API, PostgreSQL database, and FAISS vector index are fully operational."
}
```

---

### 2. Authentication

#### `POST /api/auth/login`
Authenticate user with email and password to receive a JWT access token.
- **Auth**: Public
- **Request**:
```json
{
  "email": "analyst@cybershield.io",
  "password": "AnalystPass123!"
}
```
- **Response (200 OK)**:
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

#### `POST /api/auth/register`
Self-service registration for security analysts.
- **Auth**: Public
- **Request**:
```json
{
  "name": "Alice Smith",
  "email": "alice@cybershield.io",
  "password": "StrongPassword123!",
  "role": "analyst"
}
```

#### `GET /api/auth/me`
Retrieve currently authenticated user's profile.
- **Auth**: Bearer Token
- **Headers**: `Authorization: Bearer <TOKEN>`
- **Response (200 OK)**:
```json
{
  "id": 3,
  "name": "Security Analyst",
  "email": "analyst@cybershield.io",
  "role": "analyst",
  "created_at": "2026-09-29T12:00:00Z"
}
```

---

### 3. Document Management (Admin)

#### `POST /api/documents/upload`
Upload a cybersecurity document (.pdf, .docx, or .txt), extract plain text, and record metadata.
- **Auth**: Admin (`require_admin`)
- **Content-Type**: `multipart/form-data`
- **Form Fields**:
  - `file`: Binary file (.pdf, .docx, .txt)
  - `document_type`: `"threat_intelligence"` | `"incident_runbook"` | `"vulnerability_advisory"`
  - `title`: Optional custom title string
- **Response (201 Created)**:
```json
{
  "document_id": 37,
  "filename": "ssh_runbook.txt",
  "document_type": "incident_runbook",
  "extracted_text_length": 420,
  "upload_status": "success",
  "id": 37,
  "title": "Linux SSH Security Runbook",
  "file_name": "ssh_runbook.txt",
  "file_path": "uploads/f44741b5_ssh_runbook.txt",
  "uploaded_by": 2,
  "content": "Incident Runbook: Linux SSH Brute Force Containment Procedures...",
  "created_at": "2026-09-30T05:19:15.721347Z"
}
```

#### `POST /api/documents/{document_id}/process`
Splits extracted document text into sequential overlapping chunks (500–800 words).
- **Auth**: Admin
- **Query Params**: `force=false` (set `true` to overwrite existing chunks)
- **Response (200 OK)**:
```json
{
  "document_id": 37,
  "chunks_created": 1,
  "processing_status": "success",
  "message": "Document processed successfully into 1 text chunk(s)."
}
```

#### `POST /api/documents/{document_id}/embed`
Generates 384-dimensional dense semantic embeddings for chunks and updates FAISS index.
- **Auth**: Admin
- **Query Params**: `force=false`
- **Response (200 OK)**:
```json
{
  "document_id": 37,
  "chunks_embedded": 1,
  "embedding_dimension": 384,
  "status": "success",
  "message": "Generated semantic embeddings for 1 document chunk(s)."
}
```

#### `GET /api/documents`
List stored documents with metadata.
- **Auth**: Authenticated (Admin / Analyst)
- **Query Params**: `skip=0`, `limit=100`, `document_type=...`

#### `GET /api/documents/{document_id}`
Retrieve a single document and full extracted text.
- **Auth**: Authenticated

#### `GET /api/documents/{document_id}/chunks`
Retrieve all text chunks for a document in sequential order.
- **Auth**: Authenticated

---

### 4. Semantic Search & Index Management

#### `GET /api/search`
Perform dense semantic vector similarity search via FAISS.
- **Auth**: Authenticated (Admin / Analyst)
- **Query Params**:
  - `q`: Search query or alert text (required)
  - `top_k`: Number of matches to return (1-100, default: 5)
- **Example Request**:
  `GET /api/search?q=How%20do%20I%20block%20an%20SSH%20brute%20force%20attack?&top_k=3`
- **Response (200 OK)**:
```json
[
  {
    "chunk_id": 58,
    "document_id": 37,
    "document_title": "Linux SSH Security Runbook",
    "chunk_content": "Incident Runbook: Linux SSH Brute Force Containment Procedures. When high volume failed SSH authentication attempts...",
    "similarity_score": 0.6697,
    "relevance_score": 0.6697
  }
]
```

#### `POST /api/search/rebuild`
Rebuild the FAISS in-memory index from PostgreSQL chunk embeddings.
- **Auth**: Admin
- **Query Params**: `auto_embed=true`

---

### 5. Cybersecurity Mitigation Retrieval

#### `POST /api/mitigation/search`
Retrieves structured, verbatim mitigation steps for an active security alert and logs the query for SOC auditing.
- **Auth**: Authenticated (Admin / Analyst)
- **Request**:
```json
{
  "alert": "Multiple failed SSH root login attempts observed on production bastion host.",
  "top_k": 3,
  "min_threshold": 0.35,
  "severity": "high"
}
```
- **Response (200 OK)**:
```json
{
  "alert": "Multiple failed SSH root login attempts observed on production bastion host.",
  "results": [
    {
      "document_id": 37,
      "document_title": "Linux SSH Security Runbook",
      "document_type": "incident_runbook",
      "chunk_id": 58,
      "mitigation_text": "Incident Runbook: Linux SSH Brute Force Containment Procedures. When high volume failed SSH authentication attempts trigger alert SEC-2026-SSH: 1. Immediately block offending remote source IP addresses in iptables and edge firewall. 2. Enforce public-key authentication only and disable PasswordAuthentication in /etc/ssh/sshd_config. 3. Rotate privileged user passwords and inspect /var/log/auth.log for compromised account footholds.",
      "relevance_score": 0.6594,
      "source_file": "ssh_runbook.txt"
    }
  ],
  "total_results": 1,
  "alert_id": 58
}
```

---

### 6. Grounded AI Mitigation Response (RAG)

#### `POST /api/mitigation/answer`
Generates a concise, strictly grounded AI mitigation summary from retrieved chunks. Zero hallucination guarantee: returns fallback if information is insufficient.
- **Auth**: Authenticated (Admin / Analyst)
- **Request**:
```json
{
  "alert": "Multiple failed SSH root login attempts observed on production bastion host.",
  "top_k": 3,
  "min_threshold": 0.35,
  "severity": "high"
}
```
- **Response (200 OK)**:
```json
{
  "alert": "Multiple failed SSH root login attempts observed on production bastion host.",
  "answer": "Based on the available security documentation, the following mitigation steps are recommended for this alert:\n\n**Source: Linux SSH Security Runbook (Incident Runbook)**\n- Immediately block offending remote source IP addresses in iptables and edge firewall.\n- Enforce public-key authentication only and disable PasswordAuthentication in /etc/ssh/sshd_config.\n- Rotate privileged user passwords and inspect /var/log/auth.log for compromised account footholds.",
  "sources": [
    {
      "document_id": 37,
      "document_title": "Linux SSH Security Runbook",
      "document_type": "incident_runbook",
      "chunk_id": 58,
      "mitigation_text": "Incident Runbook: Linux SSH Brute Force Containment Procedures...",
      "relevance_score": 0.6594,
      "source_file": "ssh_runbook.txt"
    }
  ],
  "results": [ ... ],
  "alert_id": 59
}
```

- **Fallback Behavior (Zero Hallucination)**:
  When an alert does not match available security documents with sufficient relevance score:
```json
{
  "alert": "What is the capital city of Australia?",
  "answer": "Insufficient information found in the available security documents.",
  "sources": [],
  "results": [],
  "alert_id": 60
}
```

---

## Frontend Integration Guide (for Frontend Dev)

### 1. Axios / Fetch Base Configuration
```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: process.env.VITE_API_URL || 'http://localhost:8000/api',
  withCredentials: true,
});

// Request interceptor to attach JWT
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('cybershield_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

### 2. Login & Token Storage
```javascript
async function login(email, password) {
  const response = await api.post('/auth/login', { email, password });
  localStorage.setItem('cybershield_token', response.data.access_token);
  localStorage.setItem('cybershield_user', JSON.stringify(response.data.user));
  return response.data.user;
}
```

### 3. Querying Mitigations for Alerts
```javascript
async function getMitigations(alertText) {
  // Returns grounded AI response + source citations + raw chunks
  const response = await api.post('/mitigation/answer', {
    alert: alertText,
    top_k: 5,
    min_threshold: 0.35,
    severity: 'high',
  });
  return response.data;
  // response.data.answer -> Grounded AI Markdown response
  // response.data.sources -> Array of cited document chunks
}
```

---

## Testing Suites

To execute the automated backend test suites:

```bash
cd backend

# 1. Full Day 10 End-to-End Architectural Test (Health -> Auth -> Upload -> Chunk -> Embed -> Search -> Mitigate -> RAG)
python app/test_day10_e2e_integration.py

# 2. Authentication, Security, & Role-Based Access Control
pytest app/test_day9_auth_security.py -v

# 3. Grounded AI RAG Mitigation Tests
python app/test_rag.py

# 4. Cybersecurity Mitigation Retrieval Tests
python app/test_mitigation.py

# 5. FAISS Vector Search Tests
python app/test_vector_search.py

# 6. Sentence Transformers Embedding Tests
python app/test_embeddings.py

# 7. Document Chunking & Text Cleaning Tests
python app/test_chunking.py

# 8. Document Upload & Extraction Tests (PDF, DOCX, TXT)
python app/test_documents.py
```

---

## Cloud Deployment (Render / Railway)

### Deploying to Render
1. Connect your GitHub repository to Render.
2. Click **New +** -> **Blueprint**.
3. Point to `backend/render.yaml`.
4. Render will automatically:
   - Provision a managed PostgreSQL instance (`cybershield-postgres`).
   - Provision the FastAPI web service (`cybershield-backend`).
   - Automatically configure `DATABASE_URL` with psycopg2 driver compatibility.
   - Run health checks against `/api/health`.

### Deploying to Railway
1. Click **New Project** -> **Deploy from GitHub repo**.
2. Add a **PostgreSQL** database service from Railway's template library.
3. Railway detects `backend/railway.json` and `backend/Procfile`.
4. Add environment variables in Railway dashboard:
   - `DATABASE_URL` (Reference the Railway Postgres connection URL)
   - `JWT_SECRET_KEY` (Generate random 64-char string)
   - `ALLOWED_ORIGINS` (Set to your frontend URL or `*`)

---

## Known Limitations & Production Roadmap

1. **In-Memory FAISS Index**:
   - The current FAISS index operates in-memory (`IndexFlatIP`) and is rebuilt on startup or upon request.
   - For multi-worker clusters with horizontal auto-scaling, migrate to a centralized vector store (e.g. PostgreSQL `pgvector`, Qdrant, or Milvus) to avoid per-instance index synchronization.
2. **Cold Start Model Loading**:
   - `all-MiniLM-L6-v2` takes ~2–4 seconds to load upon first inference on CPU. The model is a singleton to ensure subsequent queries execute in sub-30ms.
3. **Local File Storage**:
   - Uploaded files are saved to `backend/uploads/`. In cloud multi-instance production, attach an S3/GCS bucket for shared document object storage.
