# Session 005 – RAG Pipeline

**Status:** ✅ Completed
**Date:** 2026-07-04 – 2026-07-07
---

# Goal

Implement the Retrieval-Augmented Generation (RAG) ingestion pipeline for CRM Copilot.

This spec establishes the complete document ingestion foundation required for future semantic search, retrieval, and AI-powered question answering.

The implementation includes:

- Knowledge document management
- Document parsing
- Text chunking
- Embedding generation interface
- Vector storage layer
- Repository layer
- Database models
- Alembic migrations
- Unit tests

This completes the ingestion side of the RAG architecture. Retrieval and search observability will be implemented in Spec 006.

---

# Architecture

```
Document Upload
       │
       ▼
KnowledgeDocument
       │
       ▼
Parser
(PDF / DOCX / TXT)
       │
       ▼
Extracted Text
       │
       ▼
Chunking Strategy
       │
       ▼
DocumentChunk
       │
       ▼
Embedding Provider
       │
       ▼
Vector Store
```

---

# Database

## Added Models

### KnowledgeDocument

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

Relationship:

```
KnowledgeDocument
      │
      └── DocumentChunk[]
```

---

### DocumentChunk

Stores every chunk generated from a document.

Fields include:

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

# Enum

Implemented

```
DocumentProcessingStatus
```

Values:

- UPLOADED
- PROCESSING
- READY
- FAILED

---

# Repository Layer

Implemented

## KnowledgeDocumentRepository

Supports:

- create()
- get()
- list_by_status()
- list_by_document_type()
- update_status()
- update_processing_info()
- get_with_chunks()

---

## DocumentChunkRepository

Supports:

- bulk_create()
- get_by_document_id()
- delete_by_document_id()
- filter_by_metadata()
- similarity_search()

---

# File Processing

Created parser abstraction.

Implemented parsers:

- TXT Parser
- PDF Parser
- DOCX Parser

All parsers return:

```
ExtractedDocument
```

Containing

- extracted text
- metadata

---

# Chunking

Implemented recursive chunk splitting.

Supports configurable:

- chunk size
- overlap

Each chunk stores

- chunk index
- character offsets
- metadata

---

# Embedding Layer

Created provider abstraction.

Supports future providers such as:

- OpenAI
- HuggingFace
- Ollama
- Voyage AI

Current implementation focuses on interfaces rather than production models.

---

# Vector Store

Created vector storage abstraction.

Designed to support future implementations including:

- pgvector
- Pinecone
- Weaviate
- Qdrant

---

# Alembic

Created migrations for:

- knowledge_documents
- document_chunks

Later migration added:

- start_char
- end_char

---

# Major Issues Encountered

## 1. Missing downgrade()

One migration was missing a downgrade() implementation.

Issue:

```
AttributeError:
module has no attribute downgrade
```

Resolution:

Implemented proper downgrade function.

---

## 2. Broken migration chain

Downgrade failed because earlier migrations attempted to remove indexes that no longer existed.

Resolution:

Reviewed migration history and repaired migration chain instead of recreating the database.

---

## 3. PostgreSQL Enum Errors

Issue:

```
type documentprocessingstatus does not exist
```

Cause:

SQLAlchemy generated a new enum name different from the migration.

Resolution:

Explicitly configured:

```python
Enum(
    DocumentProcessingStatus,
    name="processing_status",
    create_type=False,
)
```

---

## 4. UUID Primary Key

Repository tests failed because KnowledgeDocument IDs were NULL.

Resolution:

Added:

```python
default=uuid.uuid4
```

to the primary key.

---

## 5. NOT NULL Constraint Failures

Repository fixtures were creating documents without required fields.

Resolution:

Updated test fixtures to include:

- title
- document_type
- source_type

---

## 6. Foreign Key Violations

Tests used:

```python
organization_id=uuid4()
owner_id=uuid4()
```

instead of actual fixture objects.

Resolution:

Replaced with:

```python
organization.id
user.id
```

throughout repository tests.

---

## 7. Parser Behavior

DOCX parser intentionally rejects empty documents.

Original tests expected successful parsing.

Decision:

Parser behavior retained because empty documents should not enter the RAG pipeline.

Tests updated to expect:

```
DocumentParsingError
```

---

# Testing

Implemented tests for

## Repository

KnowledgeDocumentRepository

- create
- status updates
- processing metadata
- filtering
- eager loading

DocumentChunkRepository

- bulk insert
- filtering
- retrieval
- deletion
- similarity search

---

## Parsers

TXT Parser

PDF Parser

DOCX Parser

Coverage includes:

- valid documents
- unicode
- missing files
- corrupt files
- unsupported formats
- empty documents

---

## Chunking

Verified:

- chunk count
- overlap
- ordering
- metadata

---

# Design Decisions

Adopted production-oriented behavior.

Examples:

- Reject empty documents.
- Preserve chunk character offsets.
- Store processing state.
- Keep parser abstraction independent from embedding providers.
- Separate document metadata from chunk storage.
- Maintain repository pattern consistency with previous specs.

---

# Current Project Progress

```
000 Database Foundations      ✅

001 Authentication & RBAC     ✅

002 CRM Core                  ✅

003 Audit & Activity          ✅

004 Streaming Chat            ✅

005 RAG Pipeline              ✅

006 Retrieval Observability   ⏳

007 AI Agent                  ⏳

008 Prompt Management         ⏳

009 AI Guardrails             ⏳

010 AI Actions                ⏳

011 Background Jobs           ⏳

012 Rate Limiting             ⏳

013 Observability             ⏳

014 AI Evaluation Framework   ⏳
```

---

# Ready for Next Spec

Next:

**Spec 006 – Retrieval Observability**

Planned work includes:

- Retrieval service
- Hybrid search
- Vector similarity search
- Retrieval scoring
- Citation generation
- Search analytics
- Retrieval telemetry
- Query logging
- Evaluation metrics
- End-to-end retrieval tests

This spec will connect the ingestion pipeline completed in Spec 005 with the AI retrieval layer used by future agents.