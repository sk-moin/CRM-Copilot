# Session 007 – AI Agent Orchestration

**Status:** ✅ Completed
**Date:** 2026-07-16 – 2026-07-18


---

# Overview

This session introduced the first production-ready AI Agent orchestration layer for CRM Copilot using **LangGraph**.

The previous architecture relied on a direct Chat → Retrieval → RAG flow. With this implementation, the system now executes requests through a graph-based workflow where each responsibility is isolated into dedicated nodes.

The primary objective was to build an extensible orchestration layer while keeping the existing Retrieval Service, RAG Chain, and Chat API reusable.

---

# Objectives

Completed objectives:

- Introduce LangGraph into the application
- Create graph-based AI execution pipeline
- Separate orchestration from business logic
- Keep RetrievalService reusable
- Keep RAGChain reusable
- Add dependency injection for Agent components
- Preserve existing chat API behaviour
- Maintain backward compatibility
- Ensure complete test coverage

---

# Architecture

## Request Flow

User

↓

Chat API

↓

AgentService

↓

AgentRunner

↓

LangGraph

├── Retrieve Node

├── Prompt Node

├── Generate Node

└── Citation Node

↓

Final AgentState

↓

Streaming Response

---

# New Files Created

## Agent Core

```
app/agent/

├── factory.py
├── runner.py
├── service.py
├── state.py
```

Purpose:

- Agent construction
- Agent execution
- Shared AgentState
- Dependency injection

---

## Graph Builder

```
app/agent/builders/

graph_builder.py
prompt_builder.py
```

Responsibilities:

- Build LangGraph
- Register nodes
- Configure execution flow
- Prompt generation

---

## LangGraph Nodes

```
app/agent/nodes/

retrieve.py
prompt.py
generate.py
citation.py
```

Responsibilities:

Retrieve Node

- Execute RetrievalService
- Store retrieved documents
- Store retrieval metadata

Prompt Node

- Generate final prompt
- Combine context

Generate Node

- Execute RAGChain
- Generate AI response
- Store token usage

Citation Node

- Extract citations
- Attach source metadata

---

## Tests

```
tests/agent/

test_agent_service.py
test_runner.py
test_nodes.py
```

Added unit tests covering:

- Agent execution
- Graph execution
- State preservation
- Error handling
- Usage tracking
- Citation generation

---

# Existing Files Updated

## API Layer

Updated:

```
app/api/chat.py
```

Changes:

- Integrated AgentService
- Preserved streaming behaviour
- Maintained SSE compatibility

---

## Dependency Injection

Updated:

```
app/api/dependencies.py
```

Added:

- AgentFactory
- AgentService
- AgentRunner
- GraphBuilder
- PromptBuilder

Dependency wiring for LangGraph.

---

## RAG Chain

Updated:

```
app/rag/chains/rag_chain.py
```

Changes:

- Added `run()` interface
- Preserved existing `generate()`
- Maintained backwards compatibility
- Standardized return types

---

## Retrieval Service

Minor updates to support Agent workflow while keeping the service reusable.

---

# AgentState

Implemented a shared graph state containing:

- conversation_id
- tenant_id
- user_id
- query
- messages
- retrieved_documents
- retrieval_metadata
- prompt
- response
- citations
- usage
- errors

This state is passed between all LangGraph nodes.

---

# Design Decisions

## LangGraph owns orchestration

Graph execution is responsible only for workflow.

Business logic remains inside services.

---

## Retrieval remains reusable

Retrieval logic was intentionally kept inside RetrievalService.

The agent simply invokes it.

---

## Prompt building isolated

Prompt generation is handled separately through PromptBuilder.

No prompt construction occurs inside graph nodes.

---

## RAGChain remains reusable

The RAG chain can still be called directly without using LangGraph.

The Agent uses the same RAG implementation.

---

## Dependency Injection

All Agent components are resolved through FastAPI dependencies.

No component directly instantiates another component.

---

# Problems Solved

During implementation several compatibility issues were resolved.

### AgentService API mismatch

Resolved differences between previous ChatService interface and new Agent interface.

---

### AgentRunner execution

Standardized execution using AgentState.

---

### RAGChain compatibility

Added `run()` while preserving `generate()` to avoid breaking existing tests.

---

### Chat Integration

Updated streaming endpoint to execute the Agent while preserving existing SSE responses.

---

### Test Compatibility

Refactored APIs to ensure all previous tests remained compatible.

---

# Testing

Executed:

- Agent tests
- RAG tests
- Chat integration tests
- Existing repository tests
- Service tests
- API tests

Final Result

✅ **307 / 307 tests passing**

---

# Future Extensions

The new orchestration layer is designed for future capabilities:

- Tool Calling
- Multi-step Planning
- Memory
- Reflection
- Human Approval
- Background Tasks
- Multi-Agent Workflows

These features can be added by introducing additional LangGraph nodes without changing the existing architecture.

---

# Outcome

Spec 007 has been successfully completed.

CRM Copilot now includes a modular, production-ready AI Agent built with LangGraph while preserving the clean architecture established in previous specifications.

The project is now ready to proceed with **Spec 008 – Prompt Management**.