from datetime import date, time

from pydantic import BaseModel, EmailStr, Field


class ChatRequest(BaseModel):
    session_id: str
    query: str


class ChatResponse(BaseModel):
    """Structured response from the agent."""

    answer: str = Field(description="The final answer to the user's query.")
    source: list[str] = Field(
        default_factory=list, description="The source of the answer."
    )


class BookInterviewRequest(BaseModel):
    full_name: str = Field(description="The full name of the candidate.")
    email: EmailStr = Field(description="The email address of the candidate.")
    interview_date: date = Field(description="The date of the interview (YYYY-MM-DD).")
    interview_time: time = Field(description="The time of the interview (HH:MM AM/PM).")
