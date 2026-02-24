from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from typing_extensions import TypedDict

from agent.llm import LLM


class ErrorResponseSchema(BaseModel):
    detail: str


class SuccessResponseSchema(BaseModel):
    status: str
    message: str
    content: str | None = None


class CommonRuntimeContext(TypedDict):
    db: AsyncSession
    redis: Redis
    llm: LLM
