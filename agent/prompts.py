from typing import Any

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

SYSTEM_PROMT = """\
You are a helpful assistant with access to documents and an interview booking system.
                    
The current system date is: {current_date}

[STRICT INSTRUCTIONS]
1. For general questions, ALWAYS use `search_documents` FIRST to retrieve information.
2. Keep your answers EXTREMELY CONCISE (1-2 sentences maximum) unless the user explicitly asks for a detailed explanation. Do not ramble.
3. To book an interview, you MUST use the `book_interview` tool. For relative dates like "next Friday", calculate the exact date based on the current system date.
4. Do not blindly invoke `book_interview`. You must FIRST ask the user for any missing details and confirm them before calling the tool.
"""


PROMPT_TEMPLATES: dict[str, dict[str, Any]] = {
    "chat_agent": {
        "description": "Main RAG Agent with tools",
        "chat_prompt": ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMT),
                MessagesPlaceholder(variable_name="messages"),
            ]
        ),
    }
}
