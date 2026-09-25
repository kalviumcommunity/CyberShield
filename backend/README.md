# CyberShield Backend

FastAPI backend foundation for CyberShield - Threat Intelligence & Incident Response Assistant.

## Project Structure

```
backend/
├── app/
│   ├── main.py              # Application entrypoint & FastAPI setup
│   ├── config.py            # Environment configuration & settings
│   ├── database.py          # SQLAlchemy database configuration placeholder
│   ├── models/              # SQLAlchemy database models (Day 2+)
│   ├── schemas/             # Pydantic request/response schemas
│   ├── routes/              # API route modules (e.g., health endpoint)
│   ├── services/            # Business logic services
│   └── utils/               # Helper utilities & error handlers
├── .env.example             # Example environment variable file
├── requirements.txt         # Python dependencies
└── README.md                # Documentation & local execution instructions
```

## Local Development Setup

### 1. Prerequisites
- Python 3.10+
- Virtual environment (`venv`)

### 2. Setup Virtual Environment

**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**On Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

### 5. Run FastAPI Application
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Test Endpoints
- **Interactive Documentation (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check Endpoint:** [http://localhost:8000/api/health](http://localhost:8000/api/health)
