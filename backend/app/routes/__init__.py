"""
API Routes Package
"""
from app.routes import auth, documents, health, mitigation, search

__all__ = [
    "auth",
    "health",
    "documents",
    "search",
    "mitigation",
]
