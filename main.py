from contextlib import asynccontextmanager
from inspect import isawaitable

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis import asyncio as aioredis
from redis.asyncio.client import Redis

from db import sessionmanager
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
    title="Agentic RAG", description="Agentic RAG", version="0.1.0", lifespan=lifespan
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


@app.get("/", tags=["Status Routes"])
async def root() -> dict:
    return {"status": "active", "message": "Agentic RAG is running"}


@app.get("/healthz", tags=["Status Routes"])
async def healthz() -> dict:
    return {"status": "ok!"}
