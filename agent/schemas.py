from datetime import date, time
from typing import Annotated

from langgraph.graph.message import add_messages
from pydantic import BaseModel, EmailStr, Field
from typing_extensions import TypedDict

from agent.llm import LLM


class InterviewBookingRequest(BaseModel):
    full_name: str = Field(description="The full name of the candidate.")
    email: EmailStr = Field(description="The email address of the candidate.")
    interview_date: date = Field(description="The date of the interview (YYYY-MM-DD).")
    interview_time: time = Field(
        description="The time of the interview in 24 hour format (HH:MM)."
    )


class DocumentSearchRequest(BaseModel):
    query: str = Field(
        description="The specific search query, question to look for in the documents."
    )


class ChatState(TypedDict):
    """State for nodes in the graph. Saved to memory."""

    messages: Annotated[list, add_messages]


class CommonRuntimeContext(TypedDict):
    llm: LLM
