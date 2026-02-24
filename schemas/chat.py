from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    thread_id: str = Field(..., description="Unique ID for the user's chat session.")
    query: str = Field(description="The user's query to the agent.")


class ChatResponse(BaseModel):
    """Structured response from the agent."""

    response: str = Field(description="The agent's response to the user's query.")
