from typing import Annotated, AsyncGenerator, Optional
from uuid import UUID, uuid4

import aiofiles
import aiofiles.tempfile as tempfile
from fastapi import Depends, HTTPException, status
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import (
    CharacterTextSplitter,
    RecursiveCharacterTextSplitter,
)
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from models import Document, DocumentStatus, Embedding, FileType
from schemas.embed_data import ChunkingMethod, ValidDocumentTypes
from settings import settings
from utils.helpers import file_exists, generate_embeddings, remove_file
from utils.logger import get_logger

logger = get_logger()


class EmbedText:
    def __init__(
        self,
        db: Annotated[AsyncSession, Depends(get_db)],
    ):
        self.db = db
        self._recursive_splitter = RecursiveCharacterTextSplitter(
            separators=[
                "\n\n",
                "\n",
                " ",
                ".",
                ",",
                "\u200b",  # Zero-width space
                "\uff0c",  # Full-width comma
                "\uff0e",  # Full-width period
                "\u3001",  # Ideographic comma
                "\u3002",  # Ideographic period
                "",
            ],
            chunk_size=300,
            chunk_overlap=30,
        )
        self._fixed_splitter = CharacterTextSplitter(
            separator="\n\n",
            chunk_size=300,
            chunk_overlap=30,
            length_function=len,
        )

    def _get_splitter(
        self, chunking_method: str
    ) -> RecursiveCharacterTextSplitter | CharacterTextSplitter:
        if chunking_method == ChunkingMethod.RECURSIVE:
            return self._recursive_splitter
        return self._fixed_splitter

    def _validate_document(self, content_type: str) -> FileType | None:
        if content_type == ValidDocumentTypes.PDF.value:
            return FileType.PDF
        if content_type == ValidDocumentTypes.TXT.value:
            return FileType.TXT
        return None

    async def _write_temp_file(self, file_bytes: bytes, suffix: str) -> str:
        async with tempfile.NamedTemporaryFile(
            suffix=suffix, mode="wb+", delete=False
        ) as tmp_file:
            await tmp_file.write(file_bytes)
            tmp_file_path = str(tmp_file.name)
        return tmp_file_path

    async def _get_paginated_embedding_models(
        self,
        chunks: list[str],
        document_id: UUID,
        page: Optional[int] = None,
        batch_size: int = 10,
        min_chars: int = 30,
    ) -> AsyncGenerator[list[Embedding], None]:
        models: list[Embedding] = []
        for i in range(0, len(chunks), batch_size):
            chunked_text = chunks[i : i + batch_size]
            filtered_chunks = [c for c in chunked_text if len(c.strip()) >= min_chars]
            if not filtered_chunks:
                continue
            embeddings = await generate_embeddings(filtered_chunks)
            if not embeddings:
                raise ValueError("Error generating embeddings.")

            for text, embedding in zip(filtered_chunks, embeddings):
                models.append(
                    Embedding(
                        document_id=document_id,
                        text=text,
                        embedding=embedding,
                        embedding_metadata={"page": page} if page else None,
                    )
                )
            yield models
            models = []

    async def _embed_pdf_file(
        self, tmp_file: str, document_id: UUID, chunking_method: str
    ) -> int:
        splitter = self._get_splitter(chunking_method)
        chunk_count = 0
        pdf_loader = PyMuPDFLoader(tmp_file)
        try:
            async for page in pdf_loader.alazy_load():
                chunks = splitter.split_text(page.page_content)
                page_num = page.metadata.get("page", 0)
                async for models in self._get_paginated_embedding_models(
                    chunks, document_id, page=page_num
                ):
                    self.db.add_all(models)
                    await self.db.commit()
                chunk_count += len(chunks)
            return chunk_count
        except Exception:
            await self.db.rollback()
            logger.exception(
                "Error embedding PDF file", extra={"document_id": str(document_id)}
            )
        return 0

    async def _embed_txt_file(
        self, tmp_file: str, document_id: UUID, chunking_method: str
    ) -> int:
        splitter = self._get_splitter(chunking_method)
        try:
            async with aiofiles.open(tmp_file, mode="rt", encoding="utf-8") as f:
                txt = await f.read()
            chunks = splitter.split_text(txt)
            async for models in self._get_paginated_embedding_models(
                chunks, document_id
            ):
                self.db.add_all(models)
                await self.db.commit()
            return len(chunks)
        except Exception:
            await self.db.rollback()
            logger.exception(
                "Error embedding TXT file", extra={"document_id": str(document_id)}
            )
        return 0

    async def embed_document(
        self,
        file_bytes: bytes,
        file_name: str,
        content_type: str,
        chunking_method: str = ChunkingMethod.RECURSIVE,
    ) -> Document:
        file_type = self._validate_document(content_type)
        if not file_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file type",
            )
        document = Document(
            id=uuid4(),
            file_name=file_name,
            file_type=file_type,
            chunking_method=chunking_method,
            embedding_model=settings.EMBEDDING_MODEL_NAME,
            chunk_count=0,
            status=DocumentStatus.PENDING,
        )
        self.db.add(document)
        await self.db.commit()

        suffix = ".pdf" if file_type == FileType.PDF else ".txt"
        tmp_file = await self._write_temp_file(file_bytes, suffix)
        try:
            if file_type == FileType.PDF:
                chunk_count = await self._embed_pdf_file(
                    tmp_file, document.id, chunking_method
                )
            else:
                chunk_count = await self._embed_txt_file(
                    tmp_file, document.id, chunking_method
                )

            document.chunk_count = chunk_count
            document.status = (
                DocumentStatus.COMPLETED if chunk_count > 0 else DocumentStatus.FAILED
            )
            await self.db.commit()
        except Exception:
            document.status = DocumentStatus.FAILED
            await self.db.commit()
            logger.exception(
                "Error embedding document", extra={"document_id": str(document.id)}
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error embedding document",
            )
        finally:
            if await file_exists(tmp_file):
                await remove_file(tmp_file)
        return document
