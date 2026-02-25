from datetime import datetime, timezone

from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.runtime import Runtime

from agent.prompts import PROMPT_TEMPLATES
from agent.schemas import ChatState, RuntimeContext
from agent.tools import book_interview, search_documents, search_documents_ivfflat
from utils.logger import get_logger

logger = get_logger()


tools = [search_documents, search_documents_ivfflat, book_interview]
tool_node = ToolNode(tools)


async def chat_node(state: ChatState, runtime: Runtime[RuntimeContext]):
    """Main chat node - handles conversation logic and tool calling."""

    llm = runtime.context.get("llm")
    if not llm:
        raise ValueError("LLM object is required.")

    agent_llm = llm.bind_tools(tools)

    prompt = PROMPT_TEMPLATES["chat_agent"]["chat_prompt"].invoke(
        {
            "messages": state["messages"],
            "current_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        }
    )

    response = await agent_llm.ainvoke(prompt)
    return {"messages": [response]}


workflow = StateGraph(state_schema=ChatState, context_schema=RuntimeContext)

workflow.add_node("chat", chat_node)
workflow.add_node("tools", tool_node)

workflow.set_entry_point("chat")
workflow.add_conditional_edges("chat", tools_condition)
workflow.add_edge("tools", "chat")


def get_graph(checkpointer=None):
    """Returns the compiled graph with optional checkpointer."""
    return workflow.compile(checkpointer=checkpointer)
