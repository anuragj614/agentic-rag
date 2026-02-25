import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request, status
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from agent.llm import LLM, get_llm
from agent.schemas import ChatState
from db import get_db, get_redis
from schemas.chat import ChatRequest, ChatResponse
from schemas.common import CommonRuntimeContext, ErrorResponseSchema
from utils.logger import get_logger

logger = get_logger()

router = APIRouter(prefix="/chat", tags=["Chat"])


async def get_compiled_graph(request: Request):
    return request.app.state.graph


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
        status.HTTP_408_REQUEST_TIMEOUT: {
            "model": ErrorResponseSchema,
            "description": "Request timed out",
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
    graph=Depends(get_compiled_graph),
    redis: Redis = Depends(get_redis),
    llm: LLM = Depends(get_llm),
) -> ChatResponse:

    context: CommonRuntimeContext = {
        "db": db,
        "redis": redis,
        "llm": llm,
    }
    try:
        config: RunnableConfig = {
            "configurable": {
                **context,
                "thread_id": request.thread_id,
            }
        }

        input_state: ChatState = {"messages": [HumanMessage(content=request.query)]}

        result = await asyncio.wait_for(
            graph.ainvoke(input_state, context=context, config=config), timeout=60.0
        )  # type: ignore

        messages = result.get("messages", [])
        response = str(messages[-1].content) if messages else "Agent failed to respond."

        return ChatResponse(response=response)
    except asyncio.TimeoutError:
        logger.error("Chat request timed out")
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="Request timed out. Please try again.",
        )
    except Exception as e:
        logger.error(
            "Error occurred while processing the request:", extra={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while processing the request.",
        )
