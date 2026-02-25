import asyncio
import os

import httpx
from httpx import TimeoutException
from openai import AsyncOpenAI

from settings import settings
from utils.logger import get_logger

logger = get_logger()


_openai_client: AsyncOpenAI | None = None
_http_client: httpx.AsyncClient | None = None


def get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY.get_secret_value())
    return _openai_client


def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient()
    return _http_client


async def generate_embeddings(
    texts: list[str], model_name: str = settings.EMBEDDING_MODEL_NAME
) -> list[list[float]] | None:

    if model_name.startswith("text-embedding"):
        if not settings.OPENAI_API_KEY.get_secret_value():
            logger.error("OpenAI API key is missing. Cannot generate embeddings.")
            return None

        try:
            openai_client = get_openai_client()
            response = await openai_client.embeddings.create(
                input=texts, model=model_name, dimensions=384
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error(
                "Failed to generate OpenAI embeddings", extra={"error": str(e)}
            )
            return None

    http_client = get_http_client()
    try:
        r = await http_client.post(
            settings.EMBEDDING_SERVICE_URL,
            json={"texts": texts},
            timeout=settings.REQUEST_TIMEOUT,
        )
        if r.status_code == 200:
            return r.json()["embeddings"]
        logger.error(
            "Error generating embeddings", extra={"status_code": r.status_code}
        )
    except TimeoutException:
        logger.error("Request to embedding service timed out")
    except httpx.HTTPError as e:
        logger.error("Failed to generate embeddings", extra={"error": str(e)})
    return None


async def file_exists(path: str) -> bool:
    return await asyncio.to_thread(os.path.exists, path)


async def remove_file(path: str) -> bool:
    try:
        await asyncio.to_thread(os.remove, path)
        return True
    except FileNotFoundError:
        return False
