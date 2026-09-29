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
