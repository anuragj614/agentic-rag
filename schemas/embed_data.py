from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel


class IngestResponse(BaseModel):
    document_id: UUID
    file_name: str
    chunk_count: int
    status: str


class ValidDocumentTypes(StrEnum):
    PDF = "application/pdf"
    TXT = "text/plain"


class ChunkingMethod(StrEnum):
    RECURSIVE = "recursive"
    FIXED = "fixed"
