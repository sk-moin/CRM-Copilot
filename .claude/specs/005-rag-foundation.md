# Spec 005 – Retrieval-Augmented Generation Foundation

---

# Goal

Implement the complete Retrieval-Augmented Generation (RAG) foundation for CRM Copilot.

This specification establishes the document ingestion pipeline, retrieval infrastructure, embedding abstractions, vector storage interfaces, and chat integration required for AI-powered conversations.

The implementation includes:

- Knowledge document management
- Document parsing
- Recursive text chunking
- Embedding provider abstraction
- Vector store abstraction
- Retrieval service
- RAG service orchestration
- Chat service integration
- Repository layer
- Database models
- Alembic migrations
- Unit tests

This completes the RAG foundation required by future AI capabilities.

Spec 006 will extend this foundation with retrieval observability, analytics, citations, evaluation, and search telemetry.

---

# Architecture

```text
                   Document Upload
                          │
                          ▼
                KnowledgeDocument
                          │
                          ▼
                    Document Parser
               (PDF / DOCX / TXT / MD)
                          │
                          ▼
                   ExtractedDocument
                          │
                          ▼
               Recursive Text Chunking
                          │
                          ▼
                   DocumentChunk
                          │
                          ▼
                 Embedding Provider
                          │
                          ▼
                     Vector Store
                          │
                          ▼
                  Retrieval Service
                          │
                          ▼
                     RAG Service
                          │
                          ▼
                    ChatService
                          │
                          ▼
               Streaming AI Response
```

---

# Database

## KnowledgeDocument

Stores uploaded document metadata.

Fields include:

- id
- tenant_id
- organization_id
- owner_id
- title
- filename
- storage_path
- document_type
- source_type
- mime_type
- file_size
- processing_status
- processing timestamps
- error_message
- chunk_count
- created_at
- updated_at

Relationship

```
KnowledgeDocument
        │
        └── DocumentChunk[]
```

---

## DocumentChunk

Stores every generated chunk.

Fields include

- id
- tenant_id
- document_id
- chunk_index
- chunk_text
- token_count
- metadata
- embedding
- start_char
- end_char
- created_at

---

# Document Processing Status

Implemented

```python
DocumentProcessingStatus
```

Values

- UPLOADED
- PROCESSING
- READY
- FAILED

---

# Repository Layer

## KnowledgeDocumentRepository

Implemented

- create()
- get()
- get_with_chunks()
- list_by_status()
- list_by_document_type()
- update_status()
- update_processing_info()

---

## DocumentChunkRepository

Implemented

- bulk_create()
- get_by_document_id()
- delete_by_document_id()
- filter_by_metadata()
- similarity_search()

---

# Document Parsing

Created parser abstraction.

Implemented parsers

- TXT
- PDF
- DOCX
- Markdown

All parsers return

```python
ExtractedDocument
```

containing

- extracted text
- metadata

Parser implementations validate documents and reject invalid or empty files.

---

# Chunking

Implemented recursive chunk splitting.

Supports configurable

- chunk size
- overlap

Each chunk stores

- chunk index
- character offsets
- metadata
- token count

Character offsets allow future citation generation.

---

# Embedding Layer

Implemented provider abstraction.

Designed to support

- OpenAI
- HuggingFace
- Ollama
- Voyage AI
- Future providers

Business logic is independent of embedding implementation.

---

# Vector Store

Implemented vector storage abstraction.

Supports future implementations including

- pgvector
- Pinecone
- Weaviate
- Qdrant
- Chroma

Current implementation focuses on interfaces and extensibility.

---

# Retrieval Layer

Implemented RetrievalService.

Responsibilities

- Generate query embeddings
- Execute semantic retrieval
- Rank retrieved chunks
- Return retrieval results to the RAG layer

Retrieval logic is isolated from ChatService.

---

# RAG Service

Implemented RAGService.

Responsibilities

- Receive user query
- Execute retrieval pipeline
- Build retrieval context
- Invoke LLM provider
- Stream provider responses
- Return provider-independent StreamChunk objects

RAGService owns all Retrieval-Augmented Generation logic.

---

# Prompt Construction

Implemented PromptBuilder.

PromptBuilder constructs

- system prompt
- conversation history
- current user message

Prompt construction remains independent from retrieval, allowing future prompt strategies without modifying ChatService.

---

# Chat Integration

ChatService now orchestrates conversations while delegating AI generation to RAGService.

ChatService responsibilities

- validate conversation ownership
- persist user messages
- load conversation history
- invoke RAGService
- stream assistant response
- persist assistant messages
- update conversation timestamps
- emit audit events

Retrieval logic is completely separated from conversation orchestration.

---

# LLM Service Layer

Implemented provider-independent streaming models.

Components include

- TokenUsage
- StreamChunk
- Base provider interface
- MockProvider

Business logic depends only on shared models rather than specific LLM vendors.

---

# Alembic

Created migrations for

- knowledge_documents
- document_chunks

Additional migration added

- start_char
- end_char

Database schema fully supports document ingestion and retrieval.

---

# Major Issues Encountered

## 1. Missing downgrade()

Issue

```text
AttributeError:
module has no attribute downgrade
```

Resolution

Implemented proper downgrade() functions for migrations.

---

## 2. Broken migration chain

Issue

Earlier migrations attempted to remove indexes that no longer existed.

Resolution

Reviewed and repaired the migration chain without recreating the database.

---

## 3. PostgreSQL Enum Errors

Issue

```text
type documentprocessingstatus does not exist
```

Resolution

Explicitly configured SQLAlchemy enums.

```python
Enum(
    DocumentProcessingStatus,
    name="processing_status",
    create_type=False,
)
```

---

## 4. UUID Primary Keys

Repository tests failed because IDs were NULL.

Resolution

Configured UUID defaults.

```python
default=uuid.uuid4
```

---

## 5. NOT NULL Constraint Failures

Repository fixtures omitted required fields.

Resolution

Updated fixtures with

- title
- document_type
- source_type

---

## 6. Foreign Key Violations

Tests used random UUIDs instead of actual fixture objects.

Resolution

Replaced generated UUIDs with

- organization.id
- user.id

---

## 7. Parser Validation

DOCX parser rejected empty documents.

Decision

Retained strict validation.

Tests updated to expect parsing errors for empty documents.

---

## 8. Async Streaming Tests

Issue

AsyncMock cannot directly mock async generators.

Resolution

Implemented async generator fixtures that yield StreamChunk objects matching production streaming behavior.

---

## 9. StreamChunk Final Chunk Design

Issue

Streaming metadata needed a provider-independent representation.

Resolution

Implemented StreamChunk.final_chunk() and computed final state through the StreamChunk model rather than provider-specific logic.

---

# Testing

Implemented unit tests for

## Repository Layer

KnowledgeDocumentRepository

- create
- filtering
- status updates
- eager loading
- processing metadata

DocumentChunkRepository

- bulk insert
- retrieval
- deletion
- filtering
- similarity search

---

## Document Parsers

- TXT
- PDF
- DOCX
- Markdown

Coverage includes

- valid documents
- unicode
- corrupt files
- unsupported formats
- missing files
- empty documents

---

## Chunking

Verified

- chunk count
- ordering
- overlap
- metadata
- character offsets

---

## LLM Layer

Verified

- MockProvider
- TokenUsage
- StreamChunk
- streaming metadata

---

## ChatService

Verified

- successful streaming
- user message persistence
- assistant message persistence
- token usage persistence
- conversation validation
- permission validation

---

All unit tests pass successfully.

---

# Design Decisions

Adopted production-oriented architecture.

Key decisions

- Separate retrieval from conversation orchestration.
- Keep PromptBuilder independent from retrieval.
- Provider-independent embedding interfaces.
- Provider-independent streaming models.
- Repository pattern maintained throughout.
- Reject invalid or empty documents.
- Preserve chunk character offsets.
- Store processing state.
- Keep ChatService lightweight.
- Delegate all AI generation to RAGService.

---


# Ready for Next Spec

## Spec 006 – Retrieval Observability

Planned implementation

- Retrieval tracing
- Hybrid search
- Vector similarity metrics
- Retrieval scoring
- Citation generation
- Search analytics
- Query logging
- Retrieval telemetry
- Evaluation metrics
- End-to-end retrieval tests

Spec 006 will build directly on the RAG foundation implemented in Spec 005 and introduce observability for every retrieval operation performed by the AI system.