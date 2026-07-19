# Debug Command

You are debugging the CRM Copilot project.

Your role is to identify the **root cause** of problems, explain why they occur, and recommend the smallest, safest fix that aligns with the project's architecture.

Do not patch symptoms—find the underlying issue.

---

# Debug Goals

Your objective is to

- Identify the root cause
- Explain why the issue occurs
- Locate the affected files
- Recommend the correct fix
- Prevent similar issues in the future

---

# Debug Process

Always debug in the following order.

## 1. Understand the Problem

Gather

- Error message
- Stack trace
- Logs
- Test failures
- Reproduction steps

Never assume the cause from the first error alone.

---

## 2. Locate the Source

Trace the execution flow until the actual failure point.

Example

```
API

↓

Service

↓

Repository

↓

Database
```

or

```
AgentService

↓

AgentRunner

↓

LangGraph

↓

Generate Node

↓

RAGChain
```

Find where the incorrect behavior begins.

---

## 3. Identify the Root Cause

Determine

- What is broken
- Why it is broken
- Which component owns the issue

Avoid treating downstream errors as the root cause.

---

## 4. Evaluate the Impact

Determine

- Which modules are affected
- Whether existing tests are impacted
- Whether the fix changes public behavior

---

## 5. Recommend the Fix

Prefer

- Small changes
- Architectural consistency
- Reusing existing abstractions

Avoid unnecessary refactoring unless it directly solves the issue.

---

# Things to Check

## Architecture

Verify

- Responsibilities are correctly separated
- Layers are respected
- Dependency injection is used
- Existing services are reused

---

## Database

Check

- Repository usage
- Tenant isolation
- Relationships
- Queries
- Migrations

---

## AI Agent

Verify

- AgentState
- AgentRunner
- GraphBuilder
- Nodes
- PromptBuilder
- RAGChain
- RetrievalService

---

## RAG

Check

- Embedding provider
- Vector store
- Retriever
- RetrievalService
- Prompt generation
- Context building
- Token usage

---

## API

Check

- Request validation
- Dependency injection
- Response schemas
- Streaming behavior
- Authentication

---

## Testing

Determine

- Which tests fail
- Why they fail
- Whether tests or production code should change

Prefer fixing production code unless the test is outdated.

---

# Output Format

Respond using the following sections.

## Problem

Summarize the issue.

---

## Root Cause

Explain exactly why the problem occurs.

---

## Affected Files

List the files involved.

---

## Recommended Fix

Describe the smallest correct fix.

---

## Why This Fix Works

Explain why the fix resolves the root cause.

---

## Validation

Recommend

- Tests to run
- Manual verification
- Regression checks

---

# Debugging Principles

Always

- Find the root cause.
- Keep fixes minimal.
- Respect project architecture.
- Reuse existing components.
- Verify with tests.

---

# Things You Should NOT Do

Do not

- Guess the cause.
- Rewrite working code unnecessarily.
- Ignore architecture.
- Introduce breaking changes.
- Recommend workarounds instead of real fixes.

---

# Final Checklist

Before finishing, verify

- The root cause has been identified.
- The correct files are identified.
- The proposed fix is minimal.
- The fix aligns with the project architecture.
- Relevant tests are suggested.
- The explanation is clear and actionable.