import sys
import os

# Add parent directory to sys.path for direct execution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, Base
from app.models import User, Document, DocumentChunk, Alert, MitigationResult


def init_db():
    """
    Initializes database tables by creating all defined SQLAlchemy models.
    """
    print("Initializing CyberShield database schema...")
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized successfully!")


if __name__ == "__main__":
    init_db()
