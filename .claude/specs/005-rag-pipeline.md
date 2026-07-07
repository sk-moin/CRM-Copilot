# Spec 005 — RAG Pipeline

## Goal

Implement a production-ready Retrieval-Augmented Generation (RAG) pipeline for CRM Copilot that enables tenant-aware semantic search over CRM knowledge and uploaded documents.

The RAG pipeline should provide the foundation for future AI capabilities including conversational memory, AI agents, prompt management, retrieval observability, guardrails, GraphRAG, and evaluation frameworks.

This specification focuses only on document ingestion, embedding generation, vector storage, and semantic retrieval. It does **not** include answer generation or agent reasoning.

---

# Context

The project currently includes:

* ✅ Database Foundations
* ✅ Authentication & RBAC
* ✅ CRM Core
* ✅ Audit & Activity
* ✅ Streaming Chat

The chat system currently communicates with an LLM but has no access to organization knowledge.

This specification introduces a retrieval layer that allows the assistant to retrieve relevant information from tenant-specific knowledge before future prompt construction.

The implementation must remain provider-agnostic and maintain the clean architecture established in previous specifications.

---

# Functional Requirements

## Knowledge Documents

Support storing knowledge from multiple sources.

Supported sources:

* CRM Notes
* Company descriptions
* Contact notes
* Opportunity notes
* Uploaded PDF
* DOCX
* Markdown
* TXT

Each document belongs to exactly one tenant.

Each document stores:

* tenant
* organization
* owner
* document type
* source type
* title
* status
* timestamps

---

## Document Processing Pipeline

Implement an offline ingestion pipeline.

Pipeline:

Upload

↓

Validation

↓

Document Parsing

↓

Text Normalization

↓

Chunking

↓

Embedding Generation

↓

Vector Storage

↓

Processing Status = READY

If any stage fails, the document should transition to the FAILED status with appropriate error information available for logging and debugging.

Each step should be independently testable.

---

## Document Parser Abstraction

Introduce a parser layer that is responsible only for extracting normalized text from uploaded files.

Architecture:

DocumentParser (abstract interface)

↓

* PDFParser
* DOCXParser
* MarkdownParser
* TextParser

Each parser implements a common interface:

`parse(file) -> ExtractedDocument`

The parser layer must be completely independent from chunking, embedding, and storage so that new document formats can be added without modifying the ingestion pipeline.

---

## Chunking

Documents must never be embedded as a single block.

Implement configurable chunking.

Each chunk stores:

* chunk id
* document id
* chunk index
* content
* token count
* metadata

Chunk size and overlap must be configurable.

---

## Embedding Generation

Implement an embedding provider abstraction.

Example providers:

* OpenAI
* Gemini
* Sentence Transformers

Business logic must never depend on a specific provider.

Embedding generation should be encapsulated behind a common interface.

---

## Vector Storage

Use PostgreSQL with pgvector.

Store one embedding per chunk.

Vector dimensions must be configurable.

The database should support:

* similarity search
* metadata filtering
* tenant isolation

---

## Metadata

Every chunk must include searchable metadata.

Required metadata:

* tenant_id
* organization_id
* document_type
* source_type
* entity_type
* entity_id
* created_by
* created_at
* tags
* version

Metadata should support future filtering without schema changes.

---

## Retrieval

Implement semantic retrieval.

Pipeline:

User Query

↓

Generate query embedding

↓

Vector similarity search

↓

Tenant filtering

↓

Metadata filtering

↓

Top-K selection

↓

Return ranked chunks

No reranking is included in this specification.

---

## Search API

Implement semantic search endpoint.

POST /rag/search

Request:

* query
* top_k
* optional filters

Response:

* retrieved chunks
* similarity score
* document information
* metadata

No LLM generation occurs here.

---

## Document Upload API

Implement upload endpoint.

POST /documents/upload

Supported file types:

* pdf
* docx
* md
* txt

Upload should:

* validate file
* store original
* process document
* create embeddings
* persist chunks

---

# Non-Functional Requirements

The implementation must be:

* asynchronous
* provider agnostic
* multi-tenant
* testable
* modular
* production-ready

Large documents should process efficiently.

Database operations should minimize unnecessary queries.

Embedding generation should be isolated from business logic.

---

# Database Changes

## Enable Extension

Enable:

pgvector

---

## New Tables

### knowledge_documents

Fields:

* id
* tenant_id
* organization_id
* owner_id
* title
* filename
* document_type
* source_type
* mime_type
* file_size
* processing_status
* created_at
* updated_at

---

### document_chunks

Fields:

* id
* tenant_id
* document_id
* chunk_index
* content
* token_count
* embedding (Vector)
* metadata (JSONB)
* created_at

---

# Repository Layer

Implement repositories.

KnowledgeDocumentRepository

Responsibilities:

* create
* update
* retrieve
* delete
* list

---

DocumentChunkRepository

Responsibilities:

* create chunks
* retrieve chunks
* similarity search
* delete
* metadata filtering

---

# Service Layer

Implement the following services.

## DocumentService

Responsible for:

* upload workflow
* processing orchestration
* persistence

---

## ChunkingService

Responsible for:

* document splitting
* overlap handling
* token estimation

---

## EmbeddingService

Responsible for:

* embedding generation
* provider selection
* batching

---

## RetrievalService

Responsible for:

* query embedding
* semantic search
* ranking
* metadata filtering

---

# AI Architecture

Implement provider abstractions.

EmbeddingProvider

Responsibilities:

* embed_query()
* embed_documents()

Concrete providers may include:

* OpenAIEmbeddingProvider
* GeminiEmbeddingProvider
* SentenceTransformerProvider

The rest of the application must depend only on the abstraction.

---

# File Processing

Support parsing:

PDF

DOCX

Markdown

TXT

Each parser should expose a common interface returning normalized text.

Parsing logic should remain independent from chunking.

---

# Security

All retrieval must enforce tenant isolation.

Documents from one tenant must never be retrievable by another tenant.

Future RBAC filtering should integrate without architectural changes.

Uploaded files must be validated before processing.

---

# Testing Requirements

Repository tests

* CRUD operations
* vector persistence
* metadata queries

Service tests

* chunk generation
* embedding workflow
* retrieval workflow

API tests

* upload endpoint
* search endpoint

Integration tests

* upload
* processing
* retrieval

---

# Acceptance Criteria

The specification is complete when:

* pgvector is enabled
* document models exist
* Alembic migration succeeds
* repositories implemented
* provider abstraction implemented
* chunking implemented
* embedding generation implemented
* vectors stored successfully
* semantic retrieval implemented
* upload endpoint functional
* search endpoint functional
* tenant isolation verified
* automated tests passing

---

# Out of Scope

The following are intentionally excluded.

* Hybrid Search
* BM25
* Cross-Encoder Reranking
* Prompt Construction
* LLM Answer Generation
* Agent Memory
* Tool Calling
* GraphRAG
* Retrieval Observability
* Prompt Management
* AI Guardrails
* Evaluation Framework
* Background Re-indexing

These features are covered by later specifications.

---

# Implementation Order

1. Enable pgvector
2. Create database models
3. Create Alembic migration
4. Implement repositories
5. Build embedding provider abstraction
6. Implement document parsers
7. Implement chunking service
8. Implement embedding service
9. Persist vectors
10. Implement retrieval service
11. Create upload endpoint
12. Create search endpoint
13. Write repository tests
14. Write service tests
15. Write API tests
16. Update project documentation

---

# Expected Outcome

Upon completion of this specification, CRM Copilot will support:

* Multi-tenant knowledge ingestion
* Document parsing
* Configurable chunking
* Embedding generation
* pgvector-based vector storage
* Metadata-aware semantic search
* Provider-independent embedding architecture
* Secure retrieval APIs
* Production-ready foundation for future AI capabilities
