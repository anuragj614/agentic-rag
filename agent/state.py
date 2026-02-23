from typing import Annotated

from langgraph.graph.message import add_messages
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from typing_extensions import TypedDict


class ChatState(TypedDict):
    """State for nodes in the graph. Saved to memory."""

    session_id: str
    messages: Annotated[list, add_messages]
    query: str
    context: str
    answer: str


class ChatContext(TypedDict):
    """Runtime dependencies injected into graph. Not saved to memory."""

    db: AsyncSession
    redis: Redis
