from fastapi import FastAPI

app = FastAPI(
    title="Agentic RAG",
    description="Agentic RAG",
    version="0.1.0",
)


@app.get("/")
async def healthz() -> dict:
    return {"status": "ok!"}
