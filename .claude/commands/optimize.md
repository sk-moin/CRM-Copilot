# Optimize Command

You are optimizing the CRM Copilot project.

Your role is to improve performance, scalability, maintainability, and resource efficiency while preserving the existing architecture and behavior.

Optimization should never change business logic unless explicitly requested.

---

# Optimization Goals

Your objective is to improve

- Performance
- Scalability
- Readability
- Maintainability
- Memory usage
- Database efficiency
- AI workflow efficiency
- Code quality

Always preserve correctness first.

---

# Optimization Process

Always analyze the implementation before making recommendations.

## 1. Understand the Current Implementation

Review

- Architecture
- Execution flow
- Dependencies
- Database interactions
- AI workflow
- Existing abstractions

Do not optimize blindly.

---

## 2. Identify Bottlenecks

Look for

- Duplicate work
- Expensive database queries
- Repeated API calls
- Blocking operations
- Memory-heavy logic
- Unnecessary object creation
- Large methods
- Tight coupling

Focus on measurable improvements.

---

## 3. Prioritize Optimizations

Recommend improvements in this order

1. Correctness
2. Performance
3. Scalability
4. Maintainability
5. Readability

Avoid premature optimization.

---

# Areas to Optimize

## Database

Review

- N+1 queries
- Missing indexes
- Duplicate queries
- Large result sets
- Transaction scope
- Repository usage

Prefer efficient queries over additional caching.

---

## API

Review

- Response time
- Validation overhead
- Dependency injection
- Streaming behavior
- Payload size

Avoid unnecessary serialization.

---

## AI Agent

Review

- LangGraph workflow
- Node execution
- State size
- Prompt construction
- Tool execution
- Workflow routing

Avoid duplicate node execution.

---

## RAG

Review

- Retrieval latency
- Embedding generation
- Vector search
- Context construction
- Prompt size
- Token usage

Reduce unnecessary retrievals whenever possible.

---

## Async Code

Check

- Blocking operations
- Await usage
- Parallel execution opportunities
- Async database usage

Never block the event loop.

---

## Memory

Look for

- Large temporary objects
- Duplicate copies
- Unnecessary allocations
- Inefficient loops

Prefer streaming over loading everything into memory.

---

## Code Quality

Improve

- Readability
- Reusability
- Separation of concerns
- Method size
- Class responsibilities

Avoid optimizing at the cost of maintainability.

---

# Output Format

Provide recommendations using the following sections.

## Summary

Brief overview of optimization opportunities.

---

## High Priority

List improvements with the highest impact.

For each item include

- Current issue
- Suggested optimization
- Expected benefit

---

## Medium Priority

List improvements that enhance maintainability or scalability.

---

## Low Priority

Optional improvements that can be implemented later.

---

## Estimated Impact

Explain how the proposed changes affect

- Performance
- Scalability
- Memory
- Maintainability
- Complexity

---

# Optimization Principles

Always

- Measure before optimizing.
- Prefer simple improvements.
- Preserve architecture.
- Reuse existing abstractions.
- Keep code readable.
- Maintain backward compatibility.

---

# Things You Should NOT Do

Do not

- Rewrite working code without measurable benefit.
- Introduce unnecessary complexity.
- Sacrifice readability for micro-optimizations.
- Break project architecture.
- Remove tests.

---

# Final Checklist

Before finishing, verify

- The optimization preserves functionality.
- The architecture remains consistent.
- Performance improvements are justified.
- Maintainability is improved.
- No unnecessary abstractions are introduced.
- Existing tests should continue to pass.
- Recommendations are practical and production-ready.