# Spec 006 – Retrieval Observability


---

# Goal

Implement a production-grade Retrieval Observability system for the CRM Copilot RAG pipeline.

The document ingestion pipeline implemented in Spec 005 provides document parsing, chunking, embedding generation, vector storage abstractions, and semantic retrieval.

However, the current retrieval pipeline operates as a black box. Once a retrieval request is executed, there is no persistent record of:

- which query was executed
- which embedding model generated the embedding
- which vector store was queried
- which document chunks were retrieved
- similarity scores returned by the vector store
- retrieval latency
- embedding latency
- reranking latency (future)
- retrieval failures
- retrieval quality metrics

Without retrieval observability it becomes difficult to:

- debug poor AI responses
- optimize chunking strategies
- evaluate embedding models
- compare vector stores
- analyze retrieval performance
- build evaluation datasets
- power future analytics dashboards

This specification introduces a transparent observability layer that automatically records every retrieval performed by the RAG pipeline.

Instrumentation must happen entirely inside the existing `RAGService`.

No business layer or API endpoint should manually create retrieval traces.

Observability failures must never interrupt normal retrieval.

---

# Objectives

Implement a Retrieval Observability subsystem capable of:

- Automatically tracing every retrieval request
- Recording embedding metadata
- Recording retrieval timings
- Recording similarity scores
- Recording retrieved chunks
- Recording retrieval failures
- Supporting future evaluation pipelines
- Providing analytics APIs
- Remaining completely transparent to callers

---

# Current Architecture

The current retrieval flow implemented in CRM Copilot is:

```

ChatService
│
▼
RAGService
│
├── EmbeddingProvider
│
├── VectorStore
│
└── Retrieved Chunks

```

This specification does **not** introduce a new retrieval pipeline.

Instead, it instruments the existing `RAGService`.

---

# Target Architecture

```

ChatService
│
▼
RAGService
│
├── RetrievalObservabilityService
│      │
│      ├── start trace
│      ├── record timings
│      ├── record retrieved chunks
│      ├── complete trace
│      └── record failures
│
├── EmbeddingProvider
│
├── VectorStore
│
└── Retrieved Chunks

```

Instrumentation must be invisible to callers.

Existing APIs and services should continue working without modification.

---

# High-Level Retrieval Flow

Every retrieval should follow the lifecycle below.

```

User Query
│
▼
Start Retrieval Trace
│
▼
Generate Embedding
│
▼
Record Embedding Latency
│
▼
Vector Search
│
▼
Record Retrieval Latency
│
▼
Record Retrieved Chunks
│
▼
Complete Retrieval Trace
│
▼
Return Search Results

```

If an exception occurs during retrieval:

```

Start Trace
│
▼
Retrieval Exception
│
▼
Mark Trace Failed
│
▼
Re-raise Original Exception

```

Observability must never swallow or replace business exceptions.

---

# Design Principles

The implementation should follow the same architectural conventions established in previous specifications.

## Repository Pattern

Database access belongs exclusively inside repository classes.

Services should never directly execute SQLAlchemy queries.

---

## Service Layer

Business logic belongs inside services.

Repositories should remain persistence-only.

---

## Dependency Injection

All repositories and services must be registered through:

```

app/api/dependencies.py

```

No service should instantiate repositories directly.

---

## Async SQLAlchemy

All repositories must use the existing async SQLAlchemy session.

Synchronous database operations are not permitted.

---

## Pydantic v2

All request and response schemas must use:

```python
model_config = ConfigDict(from_attributes=True)
```

---

## Automatic Instrumentation

Retrieval traces must be created automatically inside `RAGService`.

Callers should not be aware that observability exists.

---

## Fault Isolation

Any failure inside the observability layer must be logged and ignored.

Retrieval should continue normally whenever possible.

---

# Existing Components

The following components already exist from previous specifications and must be reused.

## Existing Models

```

KnowledgeDocument

DocumentChunk

Conversation

Message

Tenant

Organization

```

---

## Existing Services

```

ChatService

RAGService

AuditService

```

---

## Existing Abstractions

```

EmbeddingProvider

VectorStore

LLM Provider

```

No duplicate abstractions should be introduced.

---

# Database Layer

This specification introduces two additional database models that extend the existing RAG pipeline.

The models belong inside:

```

packages/database/models/

```

The repository layer belongs inside:

```

packages/database/repositories/

```

All database models should inherit from the existing project Base model and follow the conventions established in previous specifications.

---

# Database Models

Retrieval observability extends the RAG foundation implemented in Spec 005 by introducing persistent trace records for every retrieval operation.

Two new models will be added.

```
packages/database/models/

├── retrieval_trace.py
└── retrieved_chunk.py
```

Both models must inherit from the project's existing SQLAlchemy `Base` model and follow the same conventions used throughout the repository.

---

# Retrieval Status Enum

Create a new enum.

```
RetrievalTraceStatus
```

Values

```python
class RetrievalTraceStatus(str, Enum):
    STARTED = "started"
    SUCCESS = "success"
    FAILED = "failed"
```

Using a three-state lifecycle allows incomplete retrievals to be identified after crashes or unexpected shutdowns.

---

# RetrievalTrace Model

File

```
packages/database/models/retrieval_trace.py
```

Table

```
retrieval_traces
```

Purpose

Stores metadata describing an entire retrieval request from start to finish.

One retrieval request creates exactly one RetrievalTrace.

---

## Fields

| Field | Type | Notes |
|--------|------|------|
| id | UUID | Primary Key |
| tenant_id | UUID | FK → tenants.id |
| organization_id | UUID | FK → organizations.id |
| conversation_id | UUID | FK → conversations.id, nullable=True |
| query | Text | Original user query |
| embedding_provider | String(100) | OpenAI, MockEmbeddingProvider, HuggingFace |
| embedding_model | String(255) | text-embedding-3-small |
| vector_store | String(100) | pgvector, Pinecone, Qdrant |
| collection_name | String(255) | Optional vector collection/index |
| embedding_latency_ms | Float | Time spent generating embedding |
| retrieval_latency_ms | Float | Vector search latency |
| total_latency_ms | Float | End-to-end retrieval latency |
| retrieved_chunks | Integer | Number of chunks returned |
| status | Enum(RetrievalTraceStatus) | Retrieval lifecycle |
| error_message | Text | Nullable |
| trace_metadata | JSONB | Additional metadata |
| created_at | DateTime(timezone=True) | server_default=func.now() |
| updated_at | DateTime(timezone=True) | onupdate=func.now() |

---

## Relationships

```python
conversation = relationship(
    "Conversation",
    lazy="joined",
)

retrieved_chunk_records = relationship(
    "RetrievedChunk",
    back_populates="trace",
    cascade="all, delete-orphan",
)
```

---

## Indexes

Create indexes for

```
created_at

conversation_id

status

tenant_id

organization_id
```

These indexes support analytics and dashboard queries.

---

# RetrievedChunk Model

File

```
packages/database/models/retrieved_chunk.py
```

Table

```
retrieved_chunks
```

Purpose

Stores every chunk returned during a retrieval request.

Each RetrievalTrace can contain multiple RetrievedChunk records.

---

## Fields

| Field | Type | Notes |
|--------|------|------|
| id | UUID | Primary Key |
| tenant_id | UUID | FK |
| trace_id | UUID | FK → retrieval_traces.id |
| document_id | UUID | FK → knowledge_documents.id |
| chunk_id | UUID | FK → document_chunks.id |
| rank | Integer | Retrieval rank |
| retrieval_score | Float | Similarity / distance score |
| score_type | String(50) | cosine, dot_product, distance |
| document_title | String(255) | Cached for analytics |
| document_type | String(100) | Cached |
| chunk_index | Integer | Original chunk index |
| chunk_preview | Text | First 500 characters |
| chunk_metadata | JSONB | Optional metadata |
| created_at | DateTime(timezone=True) | server_default=func.now() |

---

## Relationships

```python
trace = relationship(
    "RetrievalTrace",
    back_populates="retrieved_chunk_records",
)

document = relationship(
    "KnowledgeDocument",
)

chunk = relationship(
    "DocumentChunk",
)
```

---

## Indexes

Create indexes

```
trace_id

document_id

retrieval_score

rank

tenant_id
```

These indexes optimize statistics queries and retrieval inspection APIs.

---

# Relationship Diagram

```
RetrievalTrace
       │
       │ 1
       │
       ▼
RetrievedChunk
       │
       ├────────────► KnowledgeDocument
       │
       └────────────► DocumentChunk
```

---

# Alembic Migration

Create a new migration.

```
alembic revision -m "add retrieval observability"
```

Migration responsibilities

- Create `retrieval_traces`
- Create `retrieved_chunks`
- Create enum `RetrievalTraceStatus`
- Create indexes
- Create foreign keys
- Create JSONB columns
- Register relationships

Downgrade must

- Drop indexes
- Drop foreign keys
- Drop both tables
- Drop enum type

Migration should follow the same conventions used throughout previous specifications.

---

# Validation Rules

The database layer should enforce the following validation rules where appropriate.

## Retrieval Score

```
Must be finite.

No hard restriction to 0–1.

Different vector stores return different score ranges.
```

---

## Rank

```
rank >= 1
```

---

## Latencies

```
embedding_latency_ms >= 0

retrieval_latency_ms >= 0

total_latency_ms >= 0
```

---

## Chunk Preview

Maximum

```
500 characters
```

Chunk previews exist only for debugging and analytics.

Full chunk text must remain in `DocumentChunk`.

---

## Error Message

Maximum recommended length

```
2000 characters
```

Long stack traces should be truncated before persistence.

---

# Design Decisions

Several design choices intentionally support future specifications.

## Cached Document Metadata

`document_title`, `document_type`, and `chunk_index` are duplicated inside `RetrievedChunk`.

This avoids expensive joins when building analytics dashboards.

---

## Trace Metadata

Instead of using a reserved SQLAlchemy attribute name (`metadata`), the model uses

```
trace_metadata
```

Likewise,

```
chunk_metadata
```

is used for retrieved chunk metadata.

---

## Provider Tracking

Both provider and model are stored independently.

Example

```
embedding_provider

OpenAI

embedding_model

text-embedding-3-small
```

This allows future comparisons between providers using identical models.

---

## Vector Store Tracking

Future deployments may support multiple vector stores.

The observability layer records

- vector store implementation
- collection/index name

allowing comparisons across environments.

---

# Acceptance Criteria

The database layer is complete when:

- Both models are implemented.
- Relationships work correctly.
- Alembic migration upgrades successfully.
- Downgrade restores the previous schema.
- All indexes exist.
- Async repositories can persist and query both models.
- Existing Specs 000–005 continue to function without modification.

---

# Repository Layer

The repository layer follows the same architecture introduced in previous specifications.

Repositories are responsible only for data persistence.

They must not contain business logic, analytics orchestration, or observability workflows.

All repositories belong under

```
packages/database/repositories/
```

---

# RetrievalTraceRepository

File

```
packages/database/repositories/retrieval_trace_repository.py
```

Inheritance

```python
class RetrievalTraceRepository(
    BaseRepository[RetrievalTrace]
)
```

The repository should follow the conventions used by existing repositories such as:

- ConversationRepository
- MessageRepository
- KnowledgeDocumentRepository
- DocumentChunkRepository

---

## Responsibilities

- Persist retrieval traces
- Update retrieval lifecycle
- Query traces
- Support filtering
- Support pagination
- Provide aggregate database queries

Business calculations remain inside the service layer.

---

## Public Methods

### create()

Create a new retrieval trace.

Parameters

```python
tenant_id

organization_id

conversation_id

query

embedding_provider

embedding_model

vector_store

collection_name

status
```

Returns

```
RetrievalTrace
```

---

### get_by_id()

Retrieve a trace by primary key.

Returns

```
RetrievalTrace | None
```

---

### update()

Update an existing trace.

Used internally by the observability service.

---

### delete()

Delete a trace.

Cascade deletes all RetrievedChunk records.

---

### list()

Supports

- pagination
- status filter
- conversation filter
- date range
- tenant scoping

---

### count()

Return total number of traces matching filters.

---

### mark_success()

Updates

```
status

retrieved_chunks

latencies

updated_at
```

---

### mark_failed()

Updates

```
status

error_message

updated_at
```

---

### get_by_conversation()

Returns every retrieval associated with a conversation.

Ordered

```
created_at DESC
```

---

### get_statistics()

Returns aggregate database statistics.

The repository should only execute SQL.

No response formatting.

Aggregates include

```
COUNT(*)

AVG(embedding_latency_ms)

AVG(retrieval_latency_ms)

AVG(total_latency_ms)

AVG(retrieved_chunks)

SUM(success)

SUM(failed)
```

Additional similarity statistics are obtained through the
RetrievedChunkRepository.

---

# RetrievedChunkRepository

File

```
packages/database/repositories/retrieved_chunk_repository.py
```

Inheritance

```python
class RetrievedChunkRepository(
    BaseRepository[RetrievedChunk]
)
```

---

## Responsibilities

- Persist retrieved chunks
- Query retrieved chunks
- Aggregate similarity scores
- Aggregate document usage

---

## Public Methods

### bulk_create()

Bulk inserts retrieved chunks for a retrieval trace.

Must use SQLAlchemy bulk insert operations.

Avoid individual INSERT statements.

---

### list_by_trace()

Returns every retrieved chunk ordered by

```
rank ASC
```

---

### delete_by_trace()

Deletes every chunk associated with a trace.

---

### average_score()

Returns

```
AVG(retrieval_score)
```

---

### top_documents()

Returns

```
document_id

document_title

retrieval_count

average_score
```

Ordered by retrieval frequency.

---

### document_statistics()

Returns

```
COUNT()

AVG(score)

MAX(score)

MIN(score)
```

Grouped by document.

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

The service coordinates the repository layer and instruments
the existing RAGService.

It contains all business logic related to retrieval tracing.

---

## Responsibilities

- Start retrieval traces
- Record embedding latency
- Record retrieval latency
- Record total latency
- Persist retrieved chunks
- Record failures
- Compute statistics
- Shield retrieval from observability failures

---

## Constructor

```python
RetrievalObservabilityService(
    session,
    retrieval_trace_repository,
    retrieved_chunk_repository,
)
```

Repositories should be injected through the existing dependency
injection system.

---

# Public Methods

## start_trace()

Creates an initial RetrievalTrace.

Status

```
STARTED
```

Returns

```
RetrievalTrace
```

---

## record_metrics()

Updates

```
embedding_latency_ms

retrieval_latency_ms

total_latency_ms
```

---

## record_chunks()

Accepts

```
trace

retrieved_chunks
```

Creates RetrievedChunk records using a single bulk insert.

---

## complete_trace()

Updates

```
status

retrieved_chunks

updated_at
```

Status becomes

```
SUCCESS
```

---

## fail_trace()

Updates

```
status

error_message
```

Status becomes

```
FAILED
```

---

## get_statistics()

Coordinates repository aggregate queries.

Produces

```
RetrievalStatsResponse
```

The service is responsible for

- calculating success rate
- calculating failure rate
- combining repository aggregates
- formatting API responses

---

# Fault Isolation

Every persistence operation inside the observability service must be wrapped in

```python
try:
    ...
except Exception:
    logger.exception(...)
```

Observability failures must never interrupt retrieval.

Example

```
Database unavailable

↓

Trace cannot be stored

↓

Log exception

↓

Continue retrieval

↓

Return retrieved chunks
```

---

# Instrument Existing RAGService

Spec 005 introduced

```
app/services/rag_service.py
```

Spec 006 extends this service.

Do not create a new retrieval pipeline.

Instrumentation must occur transparently inside the existing service.

---

## Current Flow

```
Receive query

↓

Generate embedding

↓

Vector search

↓

Return chunks
```

---

## New Flow

```
Receive query

↓

Start Retrieval Trace

↓

Generate embedding

↓

Record embedding latency

↓

Vector search

↓

Record retrieval latency

↓

Persist retrieved chunks

↓

Complete trace

↓

Return chunks
```

---

## Exception Flow

```
Receive query

↓

Start trace

↓

Exception

↓

Mark trace failed

↓

Log failure

↓

Re-raise original exception
```

The original exception must always propagate.

Observability must never replace business exceptions.

---

# Dependency Injection

Update

```
app/api/dependencies.py
```

Register

```python
get_retrieval_trace_repository()

get_retrieved_chunk_repository()

get_retrieval_observability_service()
```

Repositories should follow the same dependency injection
pattern used throughout the project.

---

# Logging

Each service should create

```python
logger = logging.getLogger(__name__)
```

Log

- Trace started
- Trace completed
- Retrieval failed
- Database persistence failed
- Unexpected exception

Never log

- document contents
- embeddings
- full chunk text
- API keys
- prompt contents

Only log identifiers and summary metadata.

---

# API Layer

Router

```
app/api/routes/retrieval_observability.py
```

Prefix

```
/retrieval-observability
```

Tag

```
Retrieval Observability
```

All endpoints require authenticated users.

---

## GET /retrieval-observability/traces

Returns paginated retrieval traces.

Supports filters:

```
page
size
status
conversation_id
date_from
date_to
```

Response

```json
{
  "items": [...],
  "page": 1,
  "size": 20,
  "total": 135
}
```

---

## GET /retrieval-observability/traces/{trace_id}

Returns a complete retrieval trace including:

- query
- timings
- embedding model
- vector store
- status
- metadata
- chunk count

Returns

```
404
```

if the trace does not exist.

---

## GET /retrieval-observability/traces/{trace_id}/chunks

Returns all retrieved chunks ordered by rank.

Each response item contains

```
rank
similarity_score
chunk_preview
document_id
chunk_id
metadata
```

The API must never expose:

- embedding vectors
- full document contents
- internal prompts

---

## GET /retrieval-observability/statistics

Returns aggregated retrieval metrics.

Example

```json
{
  "average_embedding_latency": 12.8,
  "average_retrieval_latency": 8.4,
  "average_total_latency": 23.6,
  "average_similarity_score": 0.81,
  "average_chunks": 5.3,
  "total_queries": 1275,
  "successful_queries": 1251,
  "failed_queries": 24,
  "success_rate": 98.1,
  "failure_rate": 1.9,
  "most_retrieved_documents": [
    {
      "document_id": "...",
      "count": 84
    }
  ]
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

Each dependency should follow the same dependency injection pattern used throughout the project.

Repositories must receive

```
AsyncSession
tenant_id
```

from existing dependencies.

---

# Logging

Create logger

```python
logger = logging.getLogger(__name__)
```

Log events

- Trace started
- Trace completed
- Retrieval failure
- Observability persistence failure
- Unexpected exceptions

Never log

- document text
- chunk contents
- embeddings
- prompts
- API keys

Only log identifiers and metrics.

---

# Validation Rules

Similarity score

```
0 <= similarity_score <= 1
```

Rank

```
rank >= 1
```

Latency

```
latency >= 0
```

Chunk preview

Maximum

```
500 characters
```

Metadata must always be JSON serializable.

---

# Performance Requirements

The observability layer must introduce minimal overhead.

Requirements

- Repository methods use Async SQLAlchemy
- Chunk persistence uses bulk inserts
- Statistics use aggregate SQL
- No N+1 queries
- Instrumentation overhead target: less than 5 ms
- Retrieval performance must remain unchanged

Observability failures must never block retrieval execution.

---

---

# Testing

All new functionality introduced in this specification must include automated
tests following the existing project testing conventions.

Directory structure:

tests/
├── unit/
│   ├── repositories/
│   │   ├── test_retrieval_trace_repository.py
│   │   └── test_retrieved_chunk_repository.py
│   │
│   └── services/
│       └── test_retrieval_observability_service.py
│
├── integration/
│   ├── test_rag_observability.py
│   └── test_retrieval_logging.py

No model-only tests are required unless model-specific logic is introduced.

---

# Repository Tests

RetrievalTraceRepository

Verify:

- create trace
- update trace
- mark completed
- mark failed
- filtering
- pagination
- ordering
- statistics aggregation
- conversation filtering
- status filtering

RetrievedChunkRepository

Verify:

- bulk insert
- retrieval by trace
- delete by trace
- average similarity
- top retrieved documents
- ordering by rank

---

# Service Tests

RetrievalObservabilityService

Verify:

- start_trace()
- complete_trace()
- fail_trace()
- record_chunks()
- get_statistics()

Additional scenarios

- observability failure does not interrupt retrieval
- repository exception is swallowed
- logger.exception() is called
- metrics stored correctly
- chunk previews truncated correctly
- similarity validation

---

# Integration Tests

Instrumentation must be verified end-to-end.

Verify:

✓ Retrieval automatically creates RetrievalTrace

✓ RetrievedChunk records created

✓ Similarity scores persisted

✓ Ranking persisted

✓ Latencies persisted

✓ Failure recorded when retrieval raises exception

✓ Retrieval still raises original exception

✓ Observability failures never interrupt retrieval

✓ ChatService continues functioning normally

---

# API Tests

Verify

GET /retrieval-observability/traces

- authentication
- pagination
- filtering
- empty results

GET /retrieval-observability/traces/{id}

- success
- not found

GET /retrieval-observability/traces/{id}/chunks

- ordering
- chunk previews
- permissions

GET /retrieval-observability/statistics

- aggregated metrics
- averages
- percentages
- top retrieved documents

---

# Performance Requirements

The observability layer must introduce minimal overhead.

Requirements

- bulk insert RetrievedChunk records
- async SQLAlchemy only
- aggregate SQL for statistics
- avoid N+1 queries
- repository methods should eagerly load relationships where appropriate
- instrumentation overhead should remain below 5 ms on average

---

# Security

Observability APIs require authenticated users.

Tenant isolation must follow the existing BaseRepository tenant filtering.

Never expose:

- embedding vectors
- raw embeddings
- API keys
- prompts
- full document text

Only expose

- metadata
- similarity score
- chunk preview
- ranking
- timings

Chunk previews should be truncated to a maximum of 500 characters.

---

# Logging

Create module logger

logger = logging.getLogger(__name__)

Log events

- trace started
- trace completed
- retrieval failed
- observability persistence failed
- unexpected exceptions

Never log:

- document contents
- embeddings
- prompt text

---

# Files to Create

packages/database/repositories/retrieval_trace_repository.py

packages/database/repositories/retrieved_chunk_repository.py

app/services/retrieval_observability_service.py

app/api/schemas/retrieval_trace.py

app/api/schemas/retrieved_chunk.py

app/api/routes/retrieval_observability.py

tests/unit/repositories/test_retrieval_trace_repository.py

tests/unit/repositories/test_retrieved_chunk_repository.py

tests/unit/services/test_retrieval_observability_service.py

tests/integration/test_rag_observability.py

tests/integration/test_retrieval_logging.py

---

# Files to Modify

packages/database/models/__init__.py

packages/database/repositories/__init__.py

app/api/schemas/__init__.py

app/api/routes/__init__.py

app/api/dependencies.py

app/main.py

app/services/rag_service.py

app/services/chat_service.py
(only if required to pass conversation_id)

alembic/versions/<revision>.py

---

# Future Compatibility

This observability layer is intentionally designed so later specifications
can reuse RetrievalTrace without schema redesign.

Future specifications that will depend on this include

Spec 007 — AI Agent

- tool execution tracing
- retrieval attribution
- reasoning inspection

Spec 008 — Prompt Management

- prompt version analytics
- retrieval effectiveness by prompt

Spec 009 — AI Guardrails

- hallucination auditing
- unsafe retrieval detection

Spec 010 — AI Actions

- retrieval provenance for actions
- approval auditing

Spec 013 — Observability

- dashboards
- latency graphs
- retrieval success metrics
- system monitoring

Spec 014 — AI Evaluation Framework

- retrieval precision
- recall evaluation
- MRR
- NDCG
- benchmark datasets
- offline evaluation

No breaking schema changes should be required by these future specifications.

---

# Acceptance Criteria

This specification is complete when:

✓ Every retrieval automatically creates a RetrievalTrace.

✓ RetrievedChunk records are automatically persisted.

✓ Similarity scores, rankings, and metadata are stored.

✓ Embedding, retrieval, and total latency are recorded.

✓ Retrieval failures are logged.

✓ Observability failures never interrupt retrieval.

✓ Statistics endpoint returns aggregated metrics.

✓ Repository, service, API, and integration tests all pass.

✓ Code follows the existing project architecture:

- packages/database models
- repository pattern
- async SQLAlchemy
- dependency injection
- service layer
- Pydantic v2
- FastAPI router conventions

✓ Overall test coverage for this specification is at least 95%.

---