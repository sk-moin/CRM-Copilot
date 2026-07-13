# Session 005 – RAG Foundation


**Status:** ✅ Completed
**Duration:** 2026-07-04 - 2026-07-07

---

# Objective

Implement the complete Retrieval-Augmented Generation (RAG) foundation for CRM Copilot.

The goal of this session was to move beyond simple document ingestion and establish the entire infrastructure required for future AI-powered retrieval.

This work provides the foundation for semantic search, AI chat, knowledge retrieval, and future autonomous agents.

---

# Work Completed

## Database Layer

Implemented the following database models.

### KnowledgeDocument

Stores uploaded document metadata including:

- title
- filename
- storage path
- processing state
- owner
- organization
- timestamps

### DocumentChunk

Stores every generated text chunk.

Each chunk includes:

- chunk index
- chunk text
- token count
- metadata
- embedding
- character offsets

---

## Processing Status

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

Implemented

## KnowledgeDocumentRepository

Supports

- create
- retrieval
- filtering
- eager loading
- processing updates
- status updates

---

## DocumentChunkRepository

Supports

- bulk creation
- retrieval
- deletion
- metadata filtering
- similarity search abstraction

---

# Document Parsing

Implemented parser abstraction.

Supported formats

- TXT
- PDF
- DOCX
- Markdown

Every parser returns

```python
ExtractedDocument
```

containing

- extracted text
- metadata

Validation rejects invalid and empty documents.

---

# Chunking

Implemented recursive chunk splitting.

Features

- configurable chunk size
- configurable overlap
- metadata preservation
- character offsets

Character offsets were intentionally preserved to support future citation generation.

---

# Embedding Infrastructure

Implemented provider abstraction.

Current implementation focuses on interfaces rather than production embedding models.

Designed to support

- OpenAI
- HuggingFace
- Ollama
- Voyage AI
- future providers

---

# Vector Store

Implemented vector storage abstraction.

Prepared for

- pgvector
- Pinecone
- Qdrant
- Weaviate
- Chroma

Business logic remains independent of vector database implementation.

---

# Retrieval Layer

Implemented RetrievalService.

Responsibilities

- embed queries
- retrieve relevant chunks
- rank retrieved results
- provide retrieval context

Retrieval remains completely isolated from ChatService.

---

# RAG Service

Implemented RAGService.

Responsibilities

- execute retrieval
- build AI context
- invoke LLM provider
- stream responses
- expose provider-independent StreamChunk objects

This becomes the single orchestration layer for Retrieval-Augmented Generation.

---

# Prompt Builder

Implemented PromptBuilder.

Builds prompts from

- system prompt
- conversation history
- latest user message

Prompt construction intentionally remains independent of retrieval.

---

# Chat Integration

Refactored ChatService.

Responsibilities retained

- validate conversation ownership
- persist user messages
- load history
- audit logging
- assistant persistence
- streaming orchestration

Responsibilities delegated

- retrieval
- context construction
- AI generation

ChatService now depends only on RAGService.

---

# Streaming Models

Implemented provider-independent models.

Added

## TokenUsage

Stores

- prompt tokens
- completion tokens
- total tokens
- model

---

## StreamChunk

Represents streamed output.

Supports

- token streaming
- finish reason
- usage metadata
- conversation id
- message id

This model is now the standard streaming contract throughout the application.

---

# Testing

Implemented comprehensive unit tests covering

## Repository Layer

KnowledgeDocumentRepository

- creation
- retrieval
- filtering
- eager loading
- processing updates

DocumentChunkRepository

- bulk creation
- retrieval
- deletion
- similarity search

---

## Parsers

Verified

- TXT
- PDF
- DOCX
- Markdown

Coverage included

- unicode
- corrupt files
- unsupported formats
- missing files
- empty documents

---

## Chunking

Verified

- overlap
- ordering
- metadata
- offsets

---

## ChatService

Verified

- successful streaming
- assistant persistence
- user persistence
- usage metadata
- invalid conversations
- permission handling

---

## Streaming

Verified

- StreamChunk generation
- TokenUsage propagation
- final metadata chunk

---

# Major Challenges

## Migration downgrade issues

Several Alembic migrations were missing downgrade implementations.

Resolved by implementing complete downgrade paths.

---

## Broken migration chain

Older migrations attempted to remove indexes that no longer existed.

Resolved by repairing migration history rather than recreating the database.

---

## PostgreSQL enum naming

SQLAlchemy generated enum names inconsistent with migration scripts.

Resolved using explicit enum configuration.

---

## UUID primary keys

KnowledgeDocument IDs were NULL during repository tests.

Resolved by configuring UUID defaults.

---

## Repository fixture failures

Several fixtures omitted required fields.

Updated fixtures to match production schema.

---

## Foreign key failures

Tests originally used random UUIDs instead of fixture objects.

Resolved by referencing actual Organization and User fixtures.

---

## Parser behavior

Empty DOCX files were intentionally rejected.

Updated tests to reflect production behavior instead of weakening parser validation.

---

## Async generator mocking

AsyncMock could not correctly emulate async generators returned by RAGService.

Replaced AsyncMock streaming with real async generator implementations.

---

## StreamChunk redesign

Originally attempted to store mutable final state.

Refactored StreamChunk to compute final state from finish_reason and usage, resulting in a cleaner provider-independent streaming API.

---

# Architectural Decisions

Several important architectural decisions were made.

- ChatService owns orchestration only.
- Retrieval logic belongs exclusively to RAGService.
- PromptBuilder remains independent from retrieval.
- Embedding providers are fully abstracted.
- Vector stores are replaceable.
- StreamChunk is the universal streaming contract.
- Repository pattern maintained consistently.
- Character offsets preserved for future citations.
- Empty documents are rejected during ingestion.

---

# Outcome

Spec 005 successfully establishes the complete Retrieval-Augmented Generation foundation for CRM Copilot.

The application now supports

- document ingestion
- parsing
- chunking
- embedding abstractions
- vector storage abstractions
- retrieval orchestration
- RAG-based chat
- provider-independent streaming
- comprehensive unit testing

All unit tests pass successfully.

---

# Next Session

## Spec 006 – Retrieval Observability

Planned work

- Retrieval tracing
- Retrieved chunk tracking
- Search analytics
- Retrieval scoring
- Hybrid search metrics
- Citation generation
- Query logging
- Evaluation metrics
- End-to-end retrieval testing

Spec 006 will introduce full observability for the retrieval pipeline built during Spec 005.