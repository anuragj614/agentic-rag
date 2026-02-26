# Findings Report: Agentic RAG System

This report covers what was built, what was tested, and what worked better based on the comparisons done during development.

---

## 1. Chunking Strategy Comparison

Both strategies were tested on a 33-page PDF document.

| Metric | Recursive | Semantic |
|---|---|---|
| Chunks produced | 297 | 86 |
| Processing start | 19:54:48.309 | 19:57:32.422 |
| Processing end | 19:54:57.317 | 19:57:59.742 |
| Total ingestion time | ~9.0 seconds | ~27.3 seconds |
| Avg. time per chunk | ~30 ms | ~318 ms |

**Recursive** splits text based on a separator hierarchy (paragraph breaks -> newlines -> spaces -> characters) with `chunk_size=300` and `chunk_overlap=30`. It's fast because there's no model involved, just string splitting. The downside is it doesn't understand context, so a single semantic meaning can easily get split across two chunks.

**Semantic** groups sentences by meaning using the embedding model to detect topic shifts. It took about 3× longer because every sentence needs to be embedded first. But it produced 71% fewer chunks, and each chunk covers a complete thought rather than an arbitrary character window.

**Conclusion:** Recursive is better when you need fast ingestion. Semantic is better for retrieval quality since the chunks are more meaningful. Since ingestion is a one-time cost, semantic chunking is the recommended default here.

---

## 2. Embedding Model

The system uses `all-MiniLM-L12-v2` hosted as a local microservice on port 8081.

| Property | Value |
|---|---|
| Dimensions | 384 |
| Parameters | ~33M |
| Hosting | Self-hosted (sentence-transformers) |
| Cost | Free after initial download |
| Avg. latency (batch of 10) | ~50–120 ms on CPU |

It's a lightweight model that works well for general-purpose retrieval. Since it runs locally, no data leaves the network, which is useful for privacy-sensitive documents. It does struggle a bit with very domain-specific content (legal, medical, code), but for general use it's a solid baseline.

The system also supports OpenAI embeddings(`text-embedding-3-small`) via an environment variable swap, so upgrading is straightforward if retrieval quality needs to improve.

---

## 3. Similarity Search Algorithm Comparison

Both indexes are built on the same `embeddings.embedding` column using pgvector, and exposed as separate agent tools for comparison.

| Property | HNSW | IVFFlat |
|---|---|---|
| Distance metric | Cosine | L2 (Euclidean) |
| Index config | m=16, ef_construction=64 | lists=128 |
| Build time | Slower | Faster |
| Memory usage | Higher | Lower |
| Recall | High (>95% at defaults) | Varies with `probes` |

**HNSW** builds a graph-based index and does a beam search at query time. It's fast, has consistently high recall, and cosine distance is the right metric for sentence embeddings since similarity is about direction, not magnitude.

**IVFFlat** clusters vectors into 128 buckets and only searches the nearest ones at query time. It builds faster and uses less memory, but recall drops if the `probes` setting is too low. On small datasets like the 86 chunks from the test PDF, the clustering doesn't really kick in and it ends up doing a near-exhaustive scan anyway.

**Conclusion:** HNSW performed better in practice. It gave reliable results without any tuning, and worked well even on the small test corpus. IVFFlat is worth considering at very large scale (millions of vectors) when memory becomes a concern, but for this use case HNSW is the better choice.

---

## 4. Other System Decisions

**PostgreSQL + pgvector** was used as the vector store instead of a dedicated vector DB. This keeps everything in one database — document metadata, embeddings, and bookings — which simplifies deployment and keeps transactions consistent across writes. The trade-off is that dedicated vector DBs offer more filtering options and scale better past 100M+ vectors.

**LangGraph ReAct agent** was used instead of a RetrievalQA chain. The agent decides when to call retrieval as a tool, so it can skip it for simple questions or call it multiple times if needed. The interview booking flow is also handled as a tool, so everything stays in one conversational interface.

**Redis** stores the full conversation state per `thread_id` using LangGraph's `AsyncRedisSaver`. This means context survives server restarts and any process can pick up any session. One thing to watch: memory grows indefinitely per thread, so an eviction policy or TTL should be set in production.

**SMTP via aiosmtplib** sends booking confirmation emails asynchronously so it doesn't block the API response. Works fine for the scope of this project; for production, a service like SendGrid or SES would be more reliable since they handle retries and delivery tracking.

---

## 5. Summary

| Area | Choice | Why |
|---|---|---|
| Chunking | Semantic | More coherent chunks, better retrieval |
| Embedding model | all-MiniLM-L12-v2 | Free, local, good baseline |
| Similarity search | HNSW (cosine) | Better recall, works well on small and large datasets |
| Vector store | PostgreSQL + pgvector | Single DB for everything, simpler ops |
| Agent | LangGraph ReAct | Flexible tool use, no RetrievalQA coupling |
| Memory | Redis (AsyncRedisSaver) | Durable sessions, scales horizontally |
