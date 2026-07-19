---
name: implement-langgraph-node
description: Implement a LangGraph node following the CRM Copilot AI Agent architecture. Nodes should perform a single responsibility, modify AgentState, and remain reusable, deterministic, and side-effect aware.
---

# Implement LangGraph Node

## Goal

Implement a production-ready LangGraph node that follows the CRM Copilot AI Agent architecture.

Each node should perform **exactly one responsibility**, update the shared `AgentState`, and return the modified state.

Nodes should be small, reusable, and composable.

---

# Responsibilities

This skill is responsible for:

- Creating LangGraph nodes
- Reading AgentState
- Updating AgentState
- Calling services
- Performing one business step
- Returning updated state

This skill is NOT responsible for:

- Building the graph
- Dependency injection
- HTTP handling
- Database models
- Repository implementation
- Streaming responses

---

# Project Structure

LangGraph nodes are located in

```
app/agent/nodes/
```

Examples

```
retrieve.py
prompt.py
generate.py
citation.py
```

---

# Node Responsibility

Each node should have **one responsibility only**.

Good examples

Retrieve Node

- execute RetrievalService

Prompt Node

- build final prompt

Generate Node

- execute RAGChain

Citation Node

- extract citations

Bad example

```
Retrieve documents
↓

Build prompt
↓

Generate response
↓

Save conversation
```

One node should never perform all of these.

---

# Function Signature

Every node should be asynchronous.

Example

```python
async def generate_node(
    state: AgentState,
    *,
    rag_chain: RAGChain,
) -> AgentState:
```

Always accept

```
AgentState
```

Return

```
AgentState
```

---

# AgentState

Nodes communicate only through AgentState.

Read values

```python
state["query"]
```

Update values

```python
state["response"] = result.response
```

Never create a second state object.

Modify and return the existing state.

---

# Dependency Injection

Dependencies should be passed as keyword-only parameters.

Example

```python
retrieval_service: RetrievalService
```

Avoid constructing services inside nodes.

---

# Error Handling

Allow domain exceptions to propagate unless the node is explicitly responsible for recovery.

If recording failures

```python
state["errors"].append(...)
```

Do not swallow unexpected exceptions silently.

---

# Async

Nodes should always be asynchronous.

Example

```python
await retrieval_service.retrieve(...)
```

Never block the event loop.

---

# Side Effects

A node should only perform side effects related to its own responsibility.

Examples

Retrieve node

✓ Query vector store

Generate node

✓ Call LLM

Citation node

✓ Populate citations

Avoid unrelated operations.

---

# Business Logic

Business logic belongs in services.

Node responsibilities are orchestration.

Good

```python
result = await retrieval_service.retrieve(...)
```

Bad

```
SQL query

Embedding generation

Prompt engineering

inside the node
```

---

# Naming

Node file

```
retrieve.py
```

Function

```python
retrieve_node()
```

Keep names descriptive.

---

# Documentation

Each node should include

- module docstring
- function docstring

Explain responsibility, not implementation.

---

# Imports

Prefer explicit imports.

Example

```python
from app.agent.state import AgentState

from app.rag.retrieval_service import RetrievalService
```

Avoid wildcard imports.

---

# Output Requirements

Generated node should include

- imports
- module documentation
- async node function
- type hints
- state updates
- docstrings

No placeholders.

No TODO comments.

---

# Existing CRM Copilot Pattern

Retrieve Node

- reads query
- executes RetrievalService
- stores retrieved_documents
- stores retrieval_metadata

Prompt Node

- builds prompt
- stores prompt

Generate Node

- executes RAGChain
- stores response
- stores usage

Citation Node

- extracts citations
- stores citations

Follow this architecture.

---

# Code Style

Preferred

```python
result = await rag_chain.run(...)

state["response"] = result.response
state["usage"] = result.usage

return state
```

Avoid deeply nested conditionals.

Keep nodes short and focused.

---

# Validation Checklist

Before finishing verify

- Single responsibility
- Async function
- Reads AgentState
- Updates AgentState
- Returns AgentState
- No database queries
- No HTTP logic
- Dependencies injected
- Proper type hints
- Production-ready implementation