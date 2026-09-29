import enum
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class DocumentType(str, enum.Enum):
    """
    Supported document types in CyberShield.
    """
    THREAT_INTELLIGENCE = "threat_intelligence"
    INCIDENT_RUNBOOK = "incident_runbook"
    VULNERABILITY_ADVISORY = "vulnerability_advisory"


def utc_now():
    return datetime.now(timezone.utc)


class User(Base):
    """
    User entity representing platform users (security analysts, admins, etc.).
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="analyst")
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    documents = relationship("Document", back_populates="uploader", cascade="all, delete-orphan")


class Document(Base):
    """
    Document entity storing ingested cybersecurity reports, advisories, and runbooks.
    """
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    document_type = Column(
        Enum(DocumentType, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        index=True
    )
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    content = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    uploader = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    mitigations = relationship("MitigationResult", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    """
    DocumentChunk entity storing text chunks extracted from documents.
    """
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="chunks")
    mitigations = relationship("MitigationResult", back_populates="chunk", cascade="all, delete-orphan")


class Alert(Base):
    """
    Alert entity representing active security alerts triggering mitigation lookups.
    """
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    mitigations = relationship("MitigationResult", back_populates="alert", cascade="all, delete-orphan")


class MitigationResult(Base):
    """
    MitigationResult entity mapping alerts to matching documents/chunks and relevance scores.
    """
    __tablename__ = "mitigation_results"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_id = Column(Integer, ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=True, index=True)
    mitigation_text = Column(Text, nullable=False)
    relevance_score = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    alert = relationship("Alert", back_populates="mitigations")
    document = relationship("Document", back_populates="mitigations")
    chunk = relationship("DocumentChunk", back_populates="mitigations")


__all__ = [
    "Base",
    "DocumentType",
    "User",
    "Document",
    "DocumentChunk",
    "Alert",
    "MitigationResult",
]
