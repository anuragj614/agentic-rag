from datetime import date, datetime, time
from enum import StrEnum
from typing import Any, Optional
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    event,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.sql import func
from sqlalchemy.sql.sqltypes import Uuid

from schemas.embed_data import ChunkingMethod


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all models."""

    pass


# -----------File Type---------------
class FileType(StrEnum):
    PDF = "pdf"
    TXT = "txt"


class DocumentStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


# -----------Document Table-----------
class Document(Base):
    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    file_name: Mapped[str] = mapped_column(String, nullable=False)
    file_type: Mapped[FileType] = mapped_column(String, nullable=False)
    chunking_method: Mapped[ChunkingMethod] = mapped_column(String, nullable=False)
    embedding_model: Mapped[str] = mapped_column(String, nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        String, default=DocumentStatus.PENDING, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False
    )

    embeddings: Mapped[list["Embedding"]] = relationship(
        "Embedding", back_populates="document", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Document: file_name={self.file_name} type={self.file_type} status={self.status}>"


# -----------Embedding Table-----------
class Embedding(Base):
    """Stores vector chunks produced by embedding model"""

    __tablename__ = "embeddings"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("documents.id"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)
    embedding_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    document: Mapped["Document"] = relationship("Document", back_populates="embeddings")

    def __repr__(self) -> str:
        return f"<Embedding: doc={self.document_id} chunk={self.embedding_metadata}>"


@event.listens_for(Embedding, "before_insert")
def clean_embedding_text(_, __, target: Embedding) -> None:
    """Event listener to clean text before inserting Embedding."""
    if hasattr(target, "text"):
        text: str = target.text
        if text:
            text = text.replace("\x00", "")
            text = text.encode("utf-8", "ignore").decode("utf-8", "ignore")
        target.text = text


# Algorithm 1: HNSW - builds a graph structure, fast queries, higher memory

Index(
    "ix_embeddings_hnsw",
    Embedding.__table__.c.embedding,
    postgresql_using="hnsw",
    postgresql_with={"m": 16, "ef_construction": 64},
    postgresql_ops={"embedding": "vector_cosine_ops"},
)

# Algorithm 2: IVFFlat - clusters vectors into lists, faster to build, lower memory

Index(
    "ix_embeddings_ivfflat",
    Embedding.__table__.c.embedding,
    postgresql_using="ivfflat",
    postgresql_with={"lists": 128},
    postgresql_ops={"embedding": "vector_cosine_ops"},
)


# -----------InterviewBooking Table-----------
class InterviewBooking(Base):
    """Stores interview bookings captured by the RAG agent tool."""

    __tablename__ = "interview_bookings"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    interview_date: Mapped[date] = mapped_column(Date, nullable=False)
    interview_time: Mapped[time] = mapped_column(Time(timezone=False), nullable=False)
    confirmation_sent: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<InterviewBooking: {self.full_name} on {self.interview_date}>"
