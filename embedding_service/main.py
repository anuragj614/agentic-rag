from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Awaitable, Callable, cast
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

from logger import RequestContextVar, get_logger, request_ctx_var
from settings import settings

logger = get_logger()

_MODEL_NAME = "all-MiniLM-L12-v2"
_MODEL_PATH = Path("models") / _MODEL_NAME


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the embedding model at startup."""
    if _MODEL_PATH.exists():
        logger.info(
            "Embedding model loaded from disk",
            extra={"model_name": _MODEL_NAME, "model_path": _MODEL_PATH},
        )
        model = SentenceTransformer(str(_MODEL_PATH))
    else:
        try:
            logger.info(
                "Downloading embedding model from Hugging Face Hub",
                extra={"model_name": _MODEL_NAME},
            )
            model = SentenceTransformer(_MODEL_NAME)
            model.save(_MODEL_PATH)
            logger.info(
                "Embedding model saved to disk",
                extra={"model_name": _MODEL_NAME, "model_path": _MODEL_PATH},
            )
        except Exception as e:
            logger.error(
                "Failed to load embedding model",
                extra={"model_name": _MODEL_NAME, "error": str(e)},
            )
            raise e
    app.state.embedding_model = model
    yield
    del app.state.embedding_model
    logger.info("Embedding model unloaded", extra={"model_name": _MODEL_NAME})


app = FastAPI(title="Embedding Service", lifespan=lifespan)


@app.middleware("http")
async def logging_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request_id = str(uuid4())
    request_path = f"{request.method} {request.url.path}"
    request_ctx_var.set(
        RequestContextVar(request_id=request_id, request_path=request_path)
    )
    logger.info("Request log")
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/healthz", tags=["Health"])
async def healthz() -> dict:
    return {"status": "ok!"}


class EmbeddingRequest(BaseModel):
    """Request model for creating embeddings."""

    texts: list[str]


class EmbeddingResponse(BaseModel):
    """Response model for embeddings."""

    embeddings: list[list[float]]


@app.post("/embeddings", tags=["Embeddings"])
def create_embeddings(request: Request, body: EmbeddingRequest) -> EmbeddingResponse:
    """Create embeddings"""

    try:
        model = cast(SentenceTransformer, request.app.state.embedding_model)
        embeddings = model.encode(body.texts, show_progress_bar=False).tolist()

        extra: dict[str, Any] = {"total_texts": len(body.texts)}
        if settings.DEBUG:
            extra.update({"texts": body.texts})

        logger.info("Embeddings created successfully", extra=extra)
    except Exception:
        logger.exception("Failed to create embeddings")
        raise HTTPException(status_code=500, detail="Failed to create embeddings")

    return EmbeddingResponse(embeddings=embeddings)
