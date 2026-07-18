# Spec 007 — AI Agent Orchestration (LangGraph)


**Dependencies**
- ✅ Spec 000 — Database Foundations
- ✅ Spec 001 — Authentication & RBAC
- ✅ Spec 002 — CRM Core
- ✅ Spec 003 — Audit & Activity
- ✅ Spec 004 — Streaming Chat
- ✅ Spec 005 — RAG Foundation (LangChain)
- ✅ Spec 006 — Retrieval Observability

---

# Overview

This specification introduces the AI Agent execution layer using **LangGraph**.

Unlike the current implementation where chat flows directly through the RAG chain, LangGraph will become the orchestration engine responsible for managing the complete lifecycle of an AI conversation.

The agent will coordinate retrieval, prompt construction, LLM invocation, streaming, memory, observability, and future tools while maintaining a deterministic execution graph.

This specification establishes the architecture that later specifications (Prompt Management, Guardrails, AI Actions, Evaluation, etc.) will extend without requiring major rewrites.

---

# Goals

Implement a production-ready LangGraph agent capable of:

- Managing conversation state
- Executing retrieval
- Building prompts
- Calling the LLM
- Streaming responses
- Returning citations
- Recording observability
- Supporting future tools
- Supporting future human approval
- Supporting future multi-agent workflows

---

# High-Level Architecture

```
User Message
      │
      ▼
Conversation State
      │
      ▼
Retrieve Context (LangChain)
      │
      ▼
Build Prompt
      │
      ▼
LLM Generation
      │
      ▼
Stream Response
      │
      ▼
Persist Messages
      │
      ▼
Return Response
```

Entire execution is managed by LangGraph.

---

# Objectives

Implement:

- LangGraph State
- Graph Builder
- Graph Nodes
- Graph Edges
- Agent Runner
- Chat Integration
- Streaming Support
- Retrieval Integration
- Observability Integration
- Tests

---

# Project Structure

```
app/
    agent/

        graph.py

        state.py

        runner.py

        nodes/

            retrieve.py

            prompt.py

            generate.py

            stream.py

            finish.py

        builders/

            graph_builder.py

        prompts/

            system_prompt.py

        utils/

            citations.py
```

---

# Agent State

Create a strongly typed state object.

Example fields:

```
conversation_id

tenant_id

user_id

messages

query

retrieved_documents

retrieval_metadata

context

prompt

response

citations

usage

stream

errors
```

The state becomes the shared object passed through every LangGraph node.

---

# Graph Flow

```
START

↓

Retrieve Node

↓

Prompt Node

↓

Generate Node

↓

Finish Node

↓

END
```

Future nodes can easily be inserted.

Example:

```
Retrieve

↓

Guardrails

↓

Planner

↓

Tool Execution

↓

Generate

↓

Approval

↓

Finish
```

No existing node should require modification.

---

# Node 1 — Retrieve

Responsibilities

- Receive query
- Call RetrievalService
- Receive LangChain Documents
- Save documents into state
- Save similarity scores
- Save retrieval metadata
- Save retrieval trace ID

Uses:

```
RetrievalService
```

Output:

```
state.documents

state.retrieval_metadata
```

---

# Node 2 — Prompt Builder

Responsibilities

Construct the prompt.

Inputs

- system prompt
- conversation history
- retrieved documents

Produces

```
state.prompt
```

Prompt format

```
System Prompt

Conversation

Context

Question
```

Uses LangChain prompt templates.

---

# Node 3 — Generate

Responsibilities

Invoke the LLM.

Uses

Existing LLM Provider abstraction.

Supports

- streaming
- usage
- token counting

Stores

```
state.response

state.usage
```

---

# Node 4 — Finish

Responsibilities

Finalize execution.

Tasks

Persist:

- assistant message
- citations
- usage
- timestamps

Return final response.

---

# LangGraph Builder

Create

```
graph_builder.py
```

Responsibilities

Build graph

Register nodes

Register edges

Compile graph

Returns

```
CompiledStateGraph
```

---

# Agent Runner

Create

```
runner.py
```

Responsibilities

Receive conversation

Create state

Execute graph

Return response

API

```
run()

stream()
```

This becomes the single entry point for AI execution.

---

# Streaming

Streaming must remain compatible with Spec 004.

The runner should expose

```
async for token in runner.stream(...)
```

Internally LangGraph drives execution while the LLM node streams generated tokens.

Existing API endpoints should require minimal changes.

---

# Retrieval Integration

Reuse existing implementation.

```
RetrievalService

↓

Retriever

↓

PGVectorStore

↓

DocumentChunkRepository
```

The graph should never perform retrieval directly.

Only RetrievalService handles retrieval.

---

# Observability Integration

Reuse Spec 006.

Retrieve Node automatically records:

- latency
- chunk count
- similarity
- trace

Store trace metadata inside state.

Later specifications will consume it.

---

# Prompt Management

Temporary implementation.

Create

```
system_prompt.py
```

Contains default CRM assistant prompt.

Future Spec 008 replaces this with database-managed prompts.

---

# Citations

Create utility

```
citations.py
```

Responsibilities

Extract citations from retrieved LangChain Documents.

Produces

```
[
    {
        document_id,
        chunk_id,
        title
    }
]
```

Stored inside state.

---

# Error Handling

Graph should gracefully handle

Retrieval failure

↓

LLM failure

↓

Streaming interruption

↓

Cancellation

Errors should be propagated to API.

---

# Future Extension Points

Design graph so these nodes can later be inserted.

Spec 008

Prompt Management

Spec 009

Guardrails

Spec 010

AI Actions

Spec 011

Background Jobs

Spec 013

Observability

Spec 014

Evaluation

No graph redesign should be required.

---

# Files to Create

```
app/agent/state.py

app/agent/graph.py

app/agent/runner.py

app/agent/builders/graph_builder.py

app/agent/prompts/system_prompt.py

app/agent/utils/citations.py

app/agent/nodes/retrieve.py

app/agent/nodes/prompt.py

app/agent/nodes/generate.py

app/agent/nodes/finish.py
```

---

# Existing Files to Update

```
app/api/routes/chat.py

app/services/chat_service.py

app/rag/retrieval_service.py
```

Only integrate with the new runner.

No business logic should move into the API layer.

---

# Testing

## Unit Tests

```
tests/agent/test_state.py

tests/agent/test_graph_builder.py

tests/agent/test_runner.py

tests/agent/nodes/test_retrieve.py

tests/agent/nodes/test_prompt.py

tests/agent/nodes/test_generate.py

tests/agent/nodes/test_finish.py
```

Verify

- state updates
- node execution
- graph transitions
- prompt creation
- citations
- error handling

---

## Integration Tests

```
tests/integration/test_agent_chat.py

tests/integration/test_agent_streaming.py

tests/integration/test_agent_retrieval.py
```

Verify

- complete conversation
- retrieval execution
- streaming
- citations
- observability
- persistence

---

# Design Principles

- LangGraph owns orchestration.
- LangChain owns RAG components.
- RetrievalService remains the only retrieval entry point.
- LLMProvider remains model-agnostic.
- Nodes should be small, pure, and independently testable.
- Graph should be easily extensible.
- API routes should never contain orchestration logic.

---

# Deliverables

| Component | Status |
|-----------|--------|
| Agent State | ⏳ |
| Graph Builder | ⏳ |
| LangGraph Graph | ⏳ |
| Retrieve Node | ⏳ |
| Prompt Node | ⏳ |
| Generate Node | ⏳ |
| Finish Node | ⏳ |
| Runner | ⏳ |
| Streaming | ⏳ |
| Chat Integration | ⏳ |
| Retrieval Integration | ⏳ |
| Observability Integration | ⏳ |
| Unit Tests | ⏳ |
| Integration Tests | ⏳ |

---

# Acceptance Criteria

- LangGraph orchestrates every AI conversation.
- Retrieval is executed exclusively through `RetrievalService`.
- Streaming remains compatible with Spec 004.
- Retrieval traces from Spec 006 are automatically recorded.
- Citations are generated from retrieved LangChain Documents.
- The graph is modular and supports insertion of future nodes without refactoring.
- Existing chat APIs continue to work with the new `AgentRunner`.
- All unit, repository, and integration tests pass.

---
