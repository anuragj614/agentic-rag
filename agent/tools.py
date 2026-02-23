from datetime import date, time
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Embedding, InterviewBooking
from schemas.chat import BookInterviewRequest
from services.email import email_service
from utils.helpers import generate_embeddings
from utils.logger import get_logger

logger = get_logger()


@tool
async def search_documents(query: str, config: RunnableConfig) -> str:
    """
    Search indexed documents for information relevant to the user's query.
    Always use this tool when the user asks a question about the uploaded documents.
    """
    try:
        configurable = config.get("configurable", {})

        db: AsyncSession = configurable["db"]

        query_embeddings = await generate_embeddings([query])
        if not query_embeddings:
            return "Error: Could not generate embeddings for the search query."

        query_vector = query_embeddings[0]

        # TODO: Add a similarity search using l2 distance.
        stmt = (
            select(Embedding.text)
            .order_by(Embedding.embedding.cosine_distance(query_vector))
            .limit(5)
        )

        result = await db.execute(stmt)
        chunks = result.scalars().all()

        if not chunks:
            return "No relevant information found in the knowledge base."

        return "\n\n---\n\n".join(chunks)

    except Exception as e:
        logger.exception("Error in search douments tool", extra={"error": str(e)})
        return "Error: Could not search documents."


@tool(args_schema=BookInterviewRequest)
async def book_interview(
    full_name: str,
    email: str,
    interview_date: date,
    interview_time: time,
    config: RunnableConfig,
) -> str:
    """
    Book an interview for a candidate. Requires the full name, email, interview date(YYYY-MM-DD), and interview time(HH:MM AM/PM).
    Always use this tool when the user asks to book an interview.
    Always comfirm all the details with the user before booking the interview.
    """
    try:
        configurable = config.get("configurable", {})
        db: AsyncSession = configurable["db"]

        booking = InterviewBooking(
            id=uuid4(),
            full_name=full_name,
            email=email,
            interview_date=interview_date,
            interview_time=interview_time,
            confirmation_sent=False,
        )

        db.add(booking)
        await db.commit()

        email_sent = await email_service.send_interview_booking_confirmation(booking)

        if email_sent:
            booking.confirmation_sent = True
            await db.commit()
            return f"Success! Interview booked successfully for {full_name} on {interview_date} at {interview_time}. Confirmation email sent to {email}."
        else:
            return f"Interview booked in the database for {full_name} on {interview_date} at {interview_time}. Confirmation email could not be sent to {email}. Please try again later."

    except Exception as e:
        logger.exception("Failed to book interview", extra={"error": str(e)})
        return "Error: An internal error occurred while booking the interview. Please try again later."
