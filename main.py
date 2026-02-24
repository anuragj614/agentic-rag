from contextlib import asynccontextmanager
from inspect import isawaitable

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis import asyncio as aioredis
from redis.asyncio.client import Redis

from db import sessionmanager
from routes.chat import router as chat_router
from routes.ingest import router as ingest_router
from schemas.common import ErrorResponseSchema, SuccessResponseSchema
from settings import settings
from utils.logger import get_logger

logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not sessionmanager.session_factory:
        sessionmanager.init_db()
    _redis: Redis = await aioredis.from_url(settings.REDIS_URL)
    try:
        ping_result = _redis.ping()
        await ping_result if isawaitable(ping_result) else ping_result
    except Exception as e:
        raise ConnectionError("Unable to connect to Redis") from e
    app.state.redis = _redis

    yield

    await sessionmanager.close()
    await app.state.redis.close()


app = FastAPI(
    title="Agentic RAG",
    lifespan=lifespan,
    responses={
        status.HTTP_429_TOO_MANY_REQUESTS: {
            "model": ErrorResponseSchema,
            "description": "Rate limit Response",
        }
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    return JSONResponse(
        {"detail": exc.detail},
        status_code=exc.status_code,
    )


app.include_router(ingest_router, prefix="/api", tags=["Ingestion"])
app.include_router(chat_router, prefix="/api", tags=["Chat"])


@app.get("/", tags=["Status Routes"])
async def root() -> SuccessResponseSchema:
    return SuccessResponseSchema(status="active", message="Agentic RAG is running")


@app.get("/healthz", tags=["Status Routes"])
async def healthz() -> SuccessResponseSchema:
    return SuccessResponseSchema(status="healthy", message="Health check successful")
