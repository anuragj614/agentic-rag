from pydantic import BaseModel


class ErrorResponseSchema(BaseModel):
    detail: str


class SuccessResponseSchema(BaseModel):
    status: str
    message: str
    content: str | None = None
