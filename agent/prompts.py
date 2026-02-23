from typing import Any

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

PROMPT_TEMPLATES: dict[str, dict[str, Any]] = {
    "chat_agent": {
        "description": "Main RAG Agent with tools",
        "chat_prompt": ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a helpful assistant with access to documents and an interview booking system.

                    [STRICT INSTRUCTIONS]
                    1. For general questions, ALWAYS use `search_documents` FIRST to retrieve information. Rely ONLY on retrieved information to answer.
                    2. To book an interview, you MUST use the `book_interview` tool.
                    3. Do not blindy invoke `book_interview`. You must FIRST ask the user for any missing details and confirm them before calling the tool.
                    """,
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        ),
    }
}
