from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# Database connection placeholder using SQLAlchemy.
# Configured for PostgreSQL by default via settings.DATABASE_URL.
DATABASE_URL = settings.DATABASE_URL

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args=connect_args
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """
    Dependency provider for database sessions.
    Yields a session and closes it after request completion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
