from contextlib import asynccontextmanager
from inspect import isawaitable
from typing import Awaitable, Callable
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from redis import asyncio as aioredis
from redis.asyncio.client import Redis

from agent.workflow import get_graph
from db import sessionmanager
from routes.chat import router as chat_router
from routes.ingest import router as ingest_router
from schemas.common import ErrorResponseSchema, SuccessResponseSchema
from settings import settings
from utils.helpers import _http_client
from utils.logger import RequestContextVar, get_logger, request_ctx_var

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

    checkpointer = AsyncRedisSaver(redis_client=app.state.redis)
    await checkpointer.setup()
    app.state.graph = get_graph(checkpointer=checkpointer)

    yield

    await sessionmanager.close()
    await app.state.redis.close()

    if _http_client:
        await _http_client.aclose()


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


@app.middleware("http")
async def logging_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request_id = str(uuid4())
    request_path = f"{request.method} {request.url.path}"
    request_ctx_var.set(
        RequestContextVar(request_id=request_id, request_path=request_path)
    )
    extra = {}
    if settings.ENV == "local":
        extra["query"] = request.query_params
    logger.info("Request log", extra=extra)
    response = await call_next(request)
    return response


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
