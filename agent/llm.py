from langchain_openai import ChatOpenAI

from settings import settings


class LLM:
    def __init__(
        self,
        model_name: str = settings.MODEL_NAME,
        temperature: float = settings.TEMPERATURE,
    ):
        self.llm = ChatOpenAI(
            model=model_name,
            api_key=settings.OPENAI_API_KEY,
            temperature=temperature,
            timeout=60.0,
        )

    def bind_tools(self, tools: list):
        return self.llm.bind_tools(tools)


_llm_instance: LLM | None = None


def get_llm() -> LLM:
    """Dependency to get the LLM instance."""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = LLM()
    return _llm_instance
