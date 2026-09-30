# CyberShield

CyberShield is an enterprise-grade cybersecurity threat intelligence, incident runbook, and vulnerability advisory platform that enables SOC analysts to rapidly retrieve verified, actionable mitigation steps during active security incidents.

---

## Architecture Overview

```text
React Frontend (Vite / Tailwind / Axios)
        ↓
FastAPI Backend (REST API / Async ASGI)
        ↓
JWT Authentication & Role-Based Access Control (Admin / Analyst)
        ↓
Document Management (PDF, DOCX, TXT Parsing & Extraction)
        ↓
Text Chunking (500–800 words with 60-word overlap)
        ↓
Embeddings (Sentence Transformers: all-MiniLM-L6-v2, 384-d)
        ↓
FAISS Vector Search (IndexFlatIP Inner Product / Cosine Similarity)
        ↓
Semantic Retrieval & Incident Audit Logging (PostgreSQL)
        ↓
Grounded AI Mitigation Response (Zero-hallucination RAG synthesis)
```

---

## Project Structure

```text
CyberShield/
├── backend/                  # FastAPI Backend Service (Member 2)
│   ├── app/                  # Application source code
│   │   ├── dependencies/     # Auth & Role-Based Access Control
│   │   ├── models/           # SQLAlchemy ORM Database Models
│   │   ├── routes/           # API Routers (auth, docs, search, mitigation, health)
│   │   ├── schemas/          # Pydantic v2 Request/Response Schemas
│   │   ├── services/         # Business logic (RAG, FAISS, embeddings, chunking, parsing)
│   │   └── utils/            # Shared utilities
│   ├── uploads/              # Local storage for uploaded security documents
│   ├── Dockerfile            # Production Docker container build
│   ├── Procfile              # Render / Railway / Heroku start command
│   ├── render.yaml           # Render Infrastructure Blueprint
│   ├── railway.json          # Railway deployment configuration
│   ├── requirements.txt      # Python dependencies
│   └── README.md             # Full Backend API & Integration Guide
├── docker-compose.yml        # Docker Compose configuration (PostgreSQL + FastAPI)
└── README.md                 # Project root overview
```

---

## Quick Start with Docker Compose

To launch the backend along with a managed PostgreSQL instance:

```bash
docker compose up --build -d
```

Check backend health:
```bash
curl http://localhost:8000/api/health
```

Explore interactive Swagger documentation:
- URL: [http://localhost:8000/docs](http://localhost:8000/docs)

For detailed backend setup, authentication credentials, and API documentation, refer to [`backend/README.md`](./backend/README.md).
