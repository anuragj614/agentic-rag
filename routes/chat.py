from fastapi import APIRouter, Depends, HTTPException, status
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from agent.llm import LLM, get_llm
from agent.schemas import ChatState
from agent.workflow import get_graph
from db import get_db, get_redis
from schemas.chat import ChatRequest, ChatResponse
from schemas.common import CommonRuntimeContext, ErrorResponseSchema
from utils.logger import get_logger

logger = get_logger()

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=ChatResponse,
    responses={
        status.HTTP_200_OK: {"description": "Chat response"},
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponseSchema,
            "description": "Invalid request",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponseSchema,
            "description": "Internal server error",
        },
    },
)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    llm: LLM = Depends(get_llm),
) -> ChatResponse:

    context = CommonRuntimeContext(db=db, redis=redis, llm=llm)

    try:
        checkpointer = AsyncRedisSaver(redis_client=redis)
        await checkpointer.setup()

        graph = get_graph(checkpointer=checkpointer)

        config: RunnableConfig = {
            "configurable": {
                **context,
                "thread_id": request.thread_id,
            }
        }

        input_state: ChatState = {"messages": [HumanMessage(content=request.query)]}

        result = await graph.ainvoke(input_state, config=config)  # type: ignore

        messages = result.get("messages", [])
        response = str(messages[-1].content) if messages else "Agent failed to respond."

        return ChatResponse(response=response)
    except Exception as e:
        logger.error(
            "Error occurred while processing the request:", extra={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while processing the request.",
        )
