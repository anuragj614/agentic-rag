from datetime import date, time
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.schemas import DocumentSearchRequest, InterviewBookingRequest
from models import Embedding, InterviewBooking
from services.email import email_service
from utils.helpers import generate_embeddings
from utils.logger import get_logger

logger = get_logger()


def _get_db_session(config: RunnableConfig) -> AsyncSession:
    configurable = config.get("configurable", {})
    db = configurable.get("db")
    if db is None:
        raise ValueError("Missing db session in config['configurable']['db']")
    return db


@tool(args_schema=DocumentSearchRequest)
async def search_documents(query: str, config: RunnableConfig) -> str:
    """
    This tool is for searching indexed documents using HNSW (Cosine distance) to retrieve relevant information to the user's query. This is the default search tool.
    If no relevant information is found, you MUST inform the user that you do not have any relevant information. Do not answer queries outside of the knowledge base.
    """
    try:
        db = _get_db_session(config)

        query_embeddings = await generate_embeddings([query])
        if not query_embeddings:
            return "Error: Could not generate embeddings for the search query."

        query_vector = query_embeddings[0]

        stmt = (
            select(Embedding.text)
            .where(Embedding.deleted_at.is_(None))
            .order_by(Embedding.embedding.cosine_distance(query_vector))
            .limit(5)
        )

        result = await db.execute(stmt)
        chunks = result.scalars().all()

        if not chunks:
            return "No relevant information found in the knowledge base."

        return "\n\n---\n\n".join(chunks)

    except Exception as e:
        logger.exception("Error in search documents tool", extra={"error": str(e)})
        return "Error: Could not search documents."


@tool(args_schema=DocumentSearchRequest)
async def search_documents_ivfflat(query: str, config: RunnableConfig) -> str:
    """
    This tool is for searching indexed documents using IVFFlat (L2 distance) to retrieve relevant information.
    Only use this tool when the user explicitly asks to compare search algorithms or specifically requests IVFFlat / L2 distance.
    If no relevant information is found, you MUST inform the user that you do not have any relevant information. Do not answer queries outside of the knowledge base.
    """
    try:
        db = _get_db_session(config)

        query_embeddings = await generate_embeddings([query])
        if not query_embeddings:
            return "Error: Could not generate embeddings for the search query."

        query_vector = query_embeddings[0]

        stmt = (
            select(Embedding.text)
            .where(Embedding.deleted_at.is_(None))
            .order_by(Embedding.embedding.l2_distance(query_vector))
            .limit(5)
        )

        result = await db.execute(stmt)
        chunks = result.scalars().all()

        if not chunks:
            return "No relevant information found in the knowledge base."

        return "\n\n---\n\n".join(chunks)

    except Exception as e:
        logger.exception(
            "Error in search documents ivfflat tool", extra={"error": str(e)}
        )
        return "Error: Could not search documents."


@tool(args_schema=InterviewBookingRequest)
async def book_interview(
    full_name: str,
    email: str,
    interview_date: date,
    interview_time: time,
    config: RunnableConfig,
) -> str:
    """
    This tool is for booking an interview if requested. Requires the full_name, email, interview_date(YYYY-MM-DD), and interview_time(HH:MM).
    Always use this tool when the user asks to book an interview.
    Always confirm all the details with the user before booking the interview.
    """
    try:
        db = _get_db_session(config)

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

        try:
            email_sent = await email_service.send_interview_booking_confirmation(
                booking
            )

        except Exception:
            logger.exception(
                "Failed to send interview booking confirmation email",
                extra={"booking_id": str(booking.id)},
            )
            email_sent = False
        if email_sent:
            booking.confirmation_sent = True
            await db.commit()
            return f"Success! Interview booked successfully for {full_name} on {interview_date} at {interview_time}. Confirmation email sent to {email}."

        return f"Interview booked in the database for {full_name} on {interview_date} at {interview_time}. Confirmation email could not be sent to {email}. Please try again later."

    except Exception as e:
        logger.exception("Failed to book interview", extra={"error": str(e)})
        return "Error: An internal error occurred while booking the interview. Please try again later."
