# Spec 006 – Retrieval Observability (LangSmith)

## Goal

Implement retrieval observability for the LangChain RAG pipeline.

Automatically record retrieval traces, retrieved chunks, latency, metadata, and failures without changing business logic.

---

## Components

### Models

- RetrievalTrace
- RetrievedChunk

### Repositories

- RetrievalTraceRepository
- RetrievedChunkRepository

### Service

- RetrievalService

Responsibilities:

- Execute retrieval
- Deduplicate chunks
- Rerank results
- Record metrics
- Persist RetrievalTrace
- Persist RetrievedChunk
- Return RetrievalResult

---

## Retrieval Flow

User Query
↓
Create RetrievalTrace
↓
Retriever
↓
PGVector Search
↓
Deduplicate
↓
Rerank
↓
Save Metrics
↓
Save Retrieved Chunks
↓
Return RetrievalResult

---

## Observability

Every retrieval records:

- Query
- Conversation ID
- Embedding model
- Vector store
- Latency
- Retrieved chunk count
- Retrieved chunk IDs
- Status
- Error (if any)

Failures update the trace as FAILED before re-raising the exception.

---

## Testing

Validate:

- Trace creation
- Metrics update
- Success path
- Failure path
- RetrievedChunk persistence
- Repository methods

---

## Acceptance Criteria

- RetrievalTrace created automatically
- RetrievedChunk records persisted
- Latency recorded
- Metadata recorded
- Failures tracked
- No changes required in ChatService or RAGChain