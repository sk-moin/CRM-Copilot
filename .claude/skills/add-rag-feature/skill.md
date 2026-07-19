---
name: add-rag-feature
description: Implement a Retrieval-Augmented Generation (RAG) feature following the CRM Copilot architecture. This includes retrieval, embeddings, vector search, generation, observability, and LangGraph integration while preserving the project's separation of concerns.
---

# Add RAG Feature

## Goal

Implement a production-ready RAG feature that follows the CRM Copilot architecture.

The implementation must integrate cleanly with the existing RetrievalService, RAGChain, LangGraph agent, vector store, and observability pipeline.

Every layer should have a single responsibility.

---

# Responsibilities

This skill is responsible for:

- Adding retrieval functionality
- Semantic search
- Embedding generation
- Vector store integration
- Retrieval metadata
- Citation generation
- LangGraph integration
- Retrieval observability
- Usage tracking

This skill is NOT responsible for:

- CRM business logic
- Authentication
- API routing
- Database schema unrelated to RAG
- Conversation persistence

---

# Existing Project Architecture

The CRM Copilot RAG stack already contains:

```
Document Parser

↓

Text Splitter

↓

Embedding Provider

↓

PGVector Store

↓

Retriever

↓

RetrievalService

↓

RAGChain

↓

LangGraph Agent
```

Follow this architecture.

Never bypass layers.

---

# Project Structure

Relevant folders

```
app/rag/

app/agent/

packages/database/
```

Important modules

```
embeddings/

vectorstores/

retrievers/

chains/

document_processing_service.py

retrieval_service.py
```

---

# Retrieval Flow

Always follow this pipeline

```
User Query

↓

Embedding

↓

Vector Search

↓

Retrieved Documents

↓

Prompt Construction

↓

LLM

↓

Final Response
```

Never allow the LLM to retrieve directly.

---

# Retrieval Service

Semantic retrieval belongs in

```
RetrievalService
```

Responsibilities

- measure latency
- perform retrieval
- persist retrieval traces
- persist retrieved chunks
- return RetrievalResult

Do not duplicate retrieval logic elsewhere.

---

# Retriever

Retriever is responsible only for

- semantic search
- similarity scoring
- returning documents

It should not

- build prompts
- call the LLM
- persist data

---

# Vector Store

Vector store responsibilities

- embeddings
- similarity search
- persistence
- retrieval

Avoid business logic inside vector stores.

---

# Embedding Provider

Always use the configured provider.

Never hardcode embedding models.

Current project supports

```
OpenAI

MockEmbeddingProvider
```

The embedding provider must remain configurable.

---

# LangGraph Integration

The AI Agent should receive

```
retrieved_documents

retrieval_metadata
```

through AgentState.

Do not perform retrieval inside generation nodes.

---

# Prompt Building

Prompt construction belongs to

```
PromptBuilder
```

or

```
Prompt Node
```

Avoid embedding prompt templates inside retrieval logic.

---

# RAG Chain

Responsibilities

- receive retrieved documents
- build context
- call LLM
- return response

It should never perform retrieval.

---

# Context Construction

Use retrieved documents only.

Example

```
Document 1

Document 2

Document 3
```

Never inject unrelated context.

If no documents exist

Return

```
No relevant context found.
```

---

# Citations

Citations should originate from retrieved documents.

Use metadata already stored in the documents.

Do not fabricate citations.

---

# Retrieval Observability

Whenever retrieval occurs

Record

- latency
- retrieved chunk count
- similarity scores
- embedding model
- vector store
- retrieval status
- errors
- metadata

Use

```
RetrievalTrace

RetrievedChunk
```

---

# Token Usage

Generation should capture

```
prompt_tokens

completion_tokens

total_tokens

model
```

Store usage inside AgentState.

---

# Error Handling

Wrap infrastructure failures using project-specific exceptions.

Examples

```
RetrievalError

VectorStoreError

EmbeddingError

RAGGenerationError
```

Avoid exposing provider-specific exceptions.

---

# Multi-tenancy

Every retrieval must be tenant scoped.

Never search another tenant's documents.

Use tenant-aware repositories.

---

# Async

All retrieval components should be asynchronous.

Example

```python
result = await retrieval_service.retrieve(
    query=query,
)
```

Never block the event loop.

---

# Dependency Injection

Always inject dependencies.

Good

```python
retrieval_service

rag_chain

embedding_provider

vector_store
```

Bad

```
Instantiate providers inside methods.
```

---

# Existing CRM Copilot Pattern

Document Processing

```
Parser

↓

Splitter

↓

Embeddings

↓

Vector Store
```

Retrieval

```
Retriever

↓

RetrievalService
```

Generation

```
Prompt Builder

↓

RAGChain

↓

LLM
```

Agent

```
Retrieve Node

↓

Prompt Node

↓

Generate Node

↓

Citation Node
```

Follow this architecture consistently.

---

# Output Requirements

Generated code should

- integrate with existing architecture
- reuse current services
- follow dependency injection
- support multi-tenancy
- include observability
- support configurable embeddings
- use async APIs
- include proper type hints
- include documentation

No placeholders.

No TODO comments.

No duplicated retrieval logic.

---

# Code Style

Preferred

```python
retrieval = await retrieval_service.retrieve(
    query=query,
    conversation_id=conversation_id,
)

response = await rag_chain.run(
    query=query,
    retrieval_result=retrieval,
)
```

Keep every layer focused on one responsibility.

---

# Validation Checklist

Before finishing verify

- Retrieval uses RetrievalService
- Semantic search uses Retriever
- Embeddings are configurable
- Vector store reused
- Prompt built separately
- RAGChain performs generation only
- LangGraph integration preserved
- Retrieval observability recorded
- Tenant-safe
- Async implementation
- Proper type hints
- Production-ready implementation