"""
API Routes Package
"""
from app.routes import health, documents, search, mitigation

__all__ = [
    "health",
    "documents",
    "search",
    "mitigation",
]
