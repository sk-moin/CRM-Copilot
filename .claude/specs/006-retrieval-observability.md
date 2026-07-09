# Spec 006 — Retrieval Observability


# Overview

This specification introduces **Retrieval Observability** for the RAG pipeline.

Currently, the retrieval system only returns relevant document chunks to the LLM. There is no visibility into:

- what query was executed
- which documents were searched
- which chunks were retrieved
- similarity scores
- retrieval latency
- embedding latency
- vector search latency
- retrieval failures
- retrieval quality

Production AI systems require full retrieval tracing for debugging, evaluation, prompt optimization, performance tuning, and future analytics dashboards.

This spec introduces a complete observability layer that automatically records every retrieval performed by the RAG pipeline.

No business logic should manually create traces.

Instrumentation must happen automatically inside the retrieval service.

---

# Objectives

Implement a production-grade retrieval observability system capable of:

- tracing every retrieval request
- storing timing metrics
- storing similarity scores
- storing retrieved chunks
- storing retrieval metadata
- recording failures
- exposing analytics APIs
- supporting future AI evaluation framework

---

# Architecture

```
User Query
      │
      ▼
Embedding Generation
      │
      ▼
Vector Search
      │
      ▼
Retrieved Chunks
      │
      ▼
RetrievalObservabilityService
      │
      ├── save trace
      ├── save latency
      ├── save chunk metadata
      ├── save similarity scores
      └── save errors
```

Observability must not change retrieval behavior.

Logging failures must never interrupt retrieval.

---

# Database Models

Create two new SQLAlchemy models.

---

## RetrievalTrace

File

```
app/models/retrieval_trace.py
```

Table name

```
retrieval_traces
```

Fields

| Field | Type | Notes |
|---------|------|------|
| id | UUID | PK |
| conversation_id | UUID | FK → conversations.id, nullable=True |
| query | Text | Original user query |
| embedding_model | String(255) | e.g. text-embedding-3-small |
| vector_store | String(100) | pgvector / chroma / pinecone |
| embedding_latency_ms | Float | |
| retrieval_latency_ms | Float | Vector search latency |
| total_latency_ms | Float | End-to-end retrieval latency |
| retrieved_chunks | Integer | Number of chunks returned |
| status | Enum | success / failed |
| error_message | Text | nullable |
| metadata | JSONB | Extra retrieval metadata |
| created_at | DateTime(timezone=True) | server_default=func.now() |

Relationships

```
retrieved_chunk_records = relationship(
    "RetrievedChunk",
    back_populates="trace",
    cascade="all, delete-orphan"
)
```

Indexes

- created_at
- conversation_id
- status

---

## RetrievedChunk

File

```
app/models/retrieved_chunk.py
```

Table

```
retrieved_chunks
```

Fields

| Field | Type |
|---------|------|
| id | UUID |
| trace_id | UUID FK |
| document_id | UUID FK |
| chunk_id | UUID FK |
| rank | Integer |
| similarity_score | Float |
| chunk_preview | Text |
| metadata | JSONB |
| created_at | DateTime |

Relationships

```
trace = relationship(
    "RetrievalTrace",
    back_populates="retrieved_chunk_records"
)

document = relationship("KnowledgeDocument")

chunk = relationship("DocumentChunk")
```

Indexes

- trace_id
- document_id
- similarity_score

---

# Alembic Migration

Create migration

```
alembic revision -m "add retrieval observability"
```

Migration must:

Create

```
retrieval_traces
retrieved_chunks
```

Create all indexes

Create foreign keys

Downgrade must completely remove both tables.

---

# Schemas

Directory

```
app/schemas/
```

Create

```
retrieval_trace.py
retrieved_chunk.py
```

Implement

### RetrievalTraceBase

### RetrievalTraceRead

### RetrievedChunkRead

### RetrievalStatsResponse

Fields

```
average_embedding_latency
average_retrieval_latency
average_total_latency
average_similarity_score
average_chunks
total_queries
successful_queries
failed_queries
success_rate
failure_rate
most_retrieved_documents
```

Use Pydantic v2 with

```
ConfigDict(from_attributes=True)
```

---

# Repository Layer

Directory

```
app/repositories/
```

Create

```
retrieval_trace_repository.py
retrieved_chunk_repository.py
```

---

## RetrievalTraceRepository

Methods

```
create()

update()

get()

list()

delete()

count()

get_statistics()

get_by_conversation()

mark_failed()

mark_completed()
```

Statistics query should compute

```
AVG(latencies)

AVG(similarity)

COUNT()

GROUP BY document_id

Success rate

Failure rate
```

Use SQLAlchemy aggregate functions.

---

## RetrievedChunkRepository

Methods

```
bulk_create()

list_by_trace()

delete_by_trace()

average_similarity()

top_documents()
```

Bulk insert should use SQLAlchemy bulk operations.

---

# Service Layer

Create

```
app/services/retrieval_observability_service.py
```

Class

```
RetrievalObservabilityService
```

Responsibilities

- start retrieval trace
- finish trace
- record timings
- save retrieved chunks
- record failures
- calculate statistics
- never raise logging exceptions

Public methods

```
start_trace()

complete_trace()

fail_trace()

record_chunks()

record_metrics()

get_statistics()
```

Requirements

Every database operation must be wrapped in

```
try:
    ...
except Exception:
    logger.exception(...)
```

Observability failures must never affect retrieval.

---

# Instrument Existing Retrieval Service

Modify existing RAG retrieval service.

Current flow

```
embed query

↓

vector search

↓

return chunks
```

New flow

```
start trace

↓

embedding

↓

save embedding latency

↓

vector search

↓

save vector latency

↓

record chunks

↓

complete trace

↓

return chunks
```

On exception

```
fail trace

re-raise original exception
```

Instrumentation must be transparent to callers.

---

# API Endpoints

Create router

```
app/routers/retrieval_observability.py
```

Prefix

```
/retrieval-observability
```

Tags

```
Retrieval Observability
```

Endpoints

---

## GET /retrieval-observability/traces

Supports

```
page

size

status

conversation_id

date_from

date_to
```

Returns paginated traces.

---

## GET /retrieval-observability/traces/{trace_id}

Returns

- trace
- timings
- metadata

---

## GET /retrieval-observability/traces/{trace_id}/chunks

Returns every retrieved chunk sorted by rank.

---

## GET /retrieval-observability/statistics

Returns

```
{
  "average_embedding_latency": ...,
  "average_retrieval_latency": ...,
  "average_total_latency": ...,
  "average_similarity_score": ...,
  "average_chunks": ...,
  "successful_queries": ...,
  "failed_queries": ...,
  "success_rate": ...,
  "failure_rate": ...,
  "most_retrieved_documents": [...]
}
```

---

# Dependency Injection

Update

```
app/api/dependencies.py
```

Register

```
get_retrieval_trace_repository()

get_retrieved_chunk_repository()

get_retrieval_observability_service()
```

---

# Logging

Create logger

```
logger = logging.getLogger(__name__)
```

Log

Trace started

Trace completed

Retrieval failure

Database failure

Unexpected exception

Never log document contents.

---

# Validation Rules

Similarity score

```
0 <= score <= 1
```

Latency

```
>=0
```

Rank

```
>=1
```

Chunk preview

Maximum

```
500 characters
```

---

# Performance Requirements

Bulk insert retrieved chunks.

No N+1 queries.

Repository methods must use async SQLAlchemy.

Statistics endpoint should use aggregate SQL.

Instrumentation overhead

Target

```
<5ms
```

---

# Security

Read-only APIs require authenticated users.

Do not expose:

- embedding vectors
- full chunk text
- internal prompts
- API keys

Only expose

```
chunk_preview
```

Maximum

```
500 chars
```

---

# Error Handling

Create custom exceptions if not already present

```
RetrievalTraceNotFound

ObservabilityError
```

API

```
404

400

500
```

Use existing global exception handlers.

---

# Tests

Directory

```
tests/
```

Create

```
tests/models/test_retrieval_trace.py

tests/models/test_retrieved_chunk.py

tests/repositories/test_retrieval_trace_repository.py

tests/repositories/test_retrieved_chunk_repository.py

tests/services/test_retrieval_observability_service.py

tests/api/test_retrieval_observability.py

tests/integration/test_retrieval_logging.py
```

Coverage

## Model Tests

- relationships
- constraints
- indexes
- defaults

---

## Repository Tests

- create trace
- update trace
- mark failed
- mark completed
- bulk insert chunks
- statistics query
- pagination
- filters

---

## Service Tests

- successful trace
- failed trace
- chunk recording
- latency recording
- logging failure does not interrupt retrieval

---

## API Tests

Test

```
GET traces

GET trace

GET chunks

GET statistics

404

validation

pagination

authentication
```

---

## Integration Tests

Verify

- retrieval automatically creates trace
- retrieved chunks stored
- similarity scores stored
- timings stored
- failures logged
- observability failures never break retrieval

Target test coverage

```
>=95%
```

---

# Files To Create

```
package/databases/models/retrieval_trace.py 

package/databases/models/retrieved_chunk.py 

app/api/schemas/retrieval_trace.py

app/api/schemas/retrieved_chunk.py

package/databases/repositories/retrieval_trace_repository.py 

package/databases/repositories/retrieved_chunk_repository.py 

app/services/retrieval_trace_service.py 

app/services/retrieved_chunk_service.py 

app/api/routes/retrieval_observability.py

tests/file_processing/test_retrieval_trace.py

tests/file_processing/test_retrieved_chunk.py

tests/repositories/test_retrieval_trace_repository.py

tests/repositories/test_retrieved_chunk_repository.py

tests/unit/services/test_retrieval_observability_service.py

tests/integration/test_retrieval_observability.py

tests/integration/test_retrieval_logging.py
```

---

# Files To Modify

```
app/models/__init__.py

app/schemas/__init__.py

app/repositories/__init__.py

app/services/__init__.py

app/routers/__init__.py

app/api/dependencies.py

app/main.py

app/services/rag_service.py

alembic/env.py

alembic/versions/<new_revision>.py
```

---

# Acceptance Criteria

- Every retrieval automatically creates a trace.
- Every retrieved chunk is stored with rank and similarity score.
- Latency metrics are persisted accurately.
- Retrieval failures are recorded without interrupting application flow.
- Statistics endpoint returns aggregated metrics.
- APIs support pagination and filtering.
- All repository, service, API, and integration tests pass.
- Code follows existing project architecture, async SQLAlchemy patterns, repository/service separation, dependency injection, and Pydantic v2 conventions.
- Overall test coverage for this spec is at least 95%.