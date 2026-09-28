import sys
import os

# Add parent directory to sys.path for direct execution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, inspect
from app.database import engine
from app.models import User, Document, DocumentChunk, Alert, MitigationResult, DocumentType


def test_database_connection():
    """
    Tests database connection and verifies table creation.
    """
    print("=== Testing Database Connection & Schema ===")
    try:
        # Test basic connection ping
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print(f"[OK] Database connection successful. Ping response: {result.scalar()}")

        # Inspect created tables
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"[OK] Found {len(tables)} tables in database: {tables}")

        expected_tables = {"users", "documents", "document_chunks", "alerts", "mitigation_results"}
        missing = expected_tables - set(tables)
        if missing:
            print(f"[ERROR] Missing expected tables: {missing}")
            return False

        print("[OK] All required core tables are present:")
        for table in sorted(expected_tables):
            cols = [c["name"] for c in inspector.get_columns(table)]
            print(f"  - Table '{table}': {cols}")

        print("\n=== Database Test Completed Successfully ===")
        return True
    except Exception as e:
        print(f"[ERROR] Database test failed: {e}")
        return False


if __name__ == "__main__":
    success = test_database_connection()
    if not success:
        sys.exit(1)
