# Agentic RAG

A conversational RAG (Retrieval-Augmented Generation) API built with FastAPI and LangGraph. The agent can answer questions from ingested documents and book interviews on behalf of users, using a ReAct loop with persistent conversation memory backed by Redis.

## Features

- **Document Ingestion** — Upload PDF and TXT files (up to 10MB). Documents are chunked and embedded into a pgvector database for semantic search.
- **Two Chunking Strategies** — Recursive (fast, rule-based) or Semantic (embedding-aware, groups semantically similar text).
- **Two Embedding Options** — Local `all-MiniLM-L12-v2` model via a self-hosted embedding microservice, or OpenAI `text-embedding-3-small` model.
- **Agentic Chat** — A LangGraph ReAct agent answers queries by searching ingested documents with HNSW (cosine) or IVFFlat (L2) vector indexes.
- **Interview Booking** — The agent can collect candidate details and create interview bookings, stored in PostgreSQL with an email confirmation sent via SMTP.
- **Persistent Conversation Memory** — Conversations are persisted per `thread_id` using a Redis checkpointer, enabling multi-turn chat sessions.


## Tech Stack

| Layer | Technology |
|-------|------------|
| API | FastAPI |
| Agent | LangGraph (ReAct loop) |
| LLM | OpenAI (ChatOpenAI) |
| Vector DB | PostgreSQL + pgvector |
| ORM | SQLAlchemy (async) |
| Migrations | Alembic |
| Memory | Redis (LangGraph checkpointer) |
| Embeddings | sentence-transformers / OpenAI |
| Email | aiosmtplib |
| Package manager | uv |


## Docs

| Document | Description |
|----------|-------------|
| [Findings Report](docs/findings_report.md) | Comparison of chunking strategies, embedding model, similarity search algorithms, and other system decisions |
| [Database Schema](docs/documents_table_database.md) | Full schema reference for the PostgreSQL tables |

## Prerequisites

- Python 3.12
- [uv](https://github.com/astral-sh/uv)
- Docker and Docker Compose
- An OpenAI API key

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/anuragj614/agentic-rag.git
cd agentic-rag
```

### 2. Install dependencies

```bash
make install
```

This runs `uv sync --frozen` to install all dependencies from the lockfile.

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in the required values:

```env
# App
ENV="local"
DEBUG=1

# Database (matches docker-compose defaults)
DB_URL=postgresql+asyncpg://postgres:password@localhost:5432/agentic-rag

# Redis (matches docker-compose defaults)
REDIS_URL=redis://localhost:6379

# Embedding service (local microservice — see step 5)
EMBEDDING_SERVICE_URL="http://localhost:8081/embeddings"
EMBEDDING_MODEL_NAME="all-MiniLM-L12-v2"
REQUEST_TIMEOUT=10.0

# OpenAI — required for the chat agent
OPENAI_API_KEY="sk-..."
MODEL_NAME="your-desired-model"
TEMPERATURE=0.5

# SMTP — required for interview booking confirmations
SMTP_HOST="smtp.gmail.com"
SMTP_PORT=587
SMTP_USER="you@gmail.com"
SMTP_PASSWORD="your-app-password"
SMTP_FROM_EMAIL="you@gmail.com"
```

> For Gmail, generate an [App Password](https://myaccount.google.com/apppasswords) and use it as `SMTP_PASSWORD`.


### 4. Run database migrations

```bash
make migrate
```

Creates the `documents`, `embeddings`, and `interview_bookings` tables along with HNSW and IVFFlat vector indexes.

### 5. Start the embedding service

In a separate terminal:

```bash
make embeddings
```

Starts the local sentence-transformers embedding microservice on port `8081`. Required for document ingestion when using the default `all-MiniLM-L12-v2` model.

### 6. Start the development server

```bash
make dev
```

Starts the FastAPI server on `http://localhost:8080`. API docs available at `http://localhost:8080/docs`. Also starts:
- **PostgreSQL 17** with the `pgvector` extension on port `5432`
- **Redis Stack** on port `6379` both via docker compose.

## API Reference

### Ingest a document

```
POST /api/ingest/
Content-Type: multipart/form-data
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | Yes | PDF or TXT file (max 10MB) |
| `chunking_method` | string | No | `recursive` (default) or `semantic` |
| `embedding_model` | string | No | `all-MiniLM-L12-v2` (default) or an OpenAI model name |

**Response `201`:**
```json
{
  "document_id": "uuid",
  "file_name": "example.pdf",
  "chunk_count": 42,
  "status": "completed"
}
```

### Chat with the agent

```
POST /api/chat/
Content-Type: application/json
```

```json
{
  "thread_id": "any-unique-string",
  "query": "What does the document say about onboarding?"
}
```

The `thread_id` identifies a conversation session. Reusing the same `thread_id` continues the conversation with full history.

**Response `200`:**
```json
{
  "response": "According to the documents, onboarding involves..."
}
```

### Health check

```
GET /healthz
```

## Development

| Command | Description |
|---------|-------------|
| `make lint` | Run ruff linter |
| `make format` | Auto-fix and format with ruff |
| `make mypy` | Run mypy type checks |
| `make clean` | Stop Docker containers and delete volumes |

## Using OpenAI Embeddings

To use OpenAI embeddings instead of the local model, set `embedding_model` to an OpenAI model name when ingesting:

```bash
curl -X POST http://localhost:8080/api/ingest/ \
  -F "file=@document.pdf" \
  -F "embedding_model=text-embedding-3-small" \
  -F "chunking_method=recursive"
```

Only `text-embedding-3-small` and `text-embedding-3-large` are supported as they allow dimension reduction to 384, matching the database schema.
