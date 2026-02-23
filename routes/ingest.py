from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from schemas.common import ErrorResponseSchema
from schemas.embed_data import (
    ChunkingMethod,
    EmbeddingModelChoice,
    IngestResponse,
    ValidDocumentTypes,
)
from services.embed_data import EmbedText

router = APIRouter(prefix="/ingest", tags=["Ingestion"])

MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_MIME_TYPES = {mime.value for mime in ValidDocumentTypes}


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {"description": "Document ingested successfully"},
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponseSchema,
            "description": "Invalid file type",
        },
    },
    response_model=IngestResponse,
)
async def ingest_document(
    file: Annotated[UploadFile, File(..., description="PDF or TXT file to embed")],
    chunking_method: Annotated[
        ChunkingMethod, Form(description="Chunking strategy: recursive or fixed")
    ] = ChunkingMethod.RECURSIVE,
    embedding_model: Annotated[
        EmbeddingModelChoice, Form(description="Embedding model to use")
    ] = EmbeddingModelChoice.LOCAL_MINILM,
    db: AsyncSession = Depends(get_db),
) -> IngestResponse:

    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type. Only PDF and TXT files are allowed.",
        )

    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty.",
        )

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE_MB}MB.",
        )

    embed_text = EmbedText(db=db)
    document = await embed_text.embed_document(
        file_bytes=file_bytes,
        file_name=file.filename or "unknown",
        content_type=file.content_type,
        chunking_method=chunking_method,
        embedding_model=embedding_model,
    )
    return IngestResponse(
        document_id=document.id,
        file_name=document.file_name,
        chunk_count=document.chunk_count,
        status=document.status,
    )
