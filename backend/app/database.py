from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

db_url = settings.sync_database_url

# Configure connection parameters based on database protocol (e.g. SQLite thread check)
connect_args = {}
if db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

# Initialize SQLAlchemy engine
engine = create_engine(
    db_url,
    echo=settings.DEBUG,
    connect_args=connect_args,
    pool_pre_ping=True
)

# Session factory for DB interactions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base class for models
Base = declarative_base()


def get_db():
    """
    FastAPI dependency to yield a database session per request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
