import httpx
from httpx import TimeoutException

from settings import settings
from utils.logger import get_logger

logger = get_logger()


async def generate_embeddings(texts: list[str]) -> list[list[float]] | None:
    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(
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
