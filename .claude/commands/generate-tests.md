# Generate Tests Command

You are generating tests for the CRM Copilot project.

Your role is to create reliable, maintainable, production-quality tests that validate the behavior of the system while following the existing testing architecture.

Always generate tests that integrate naturally into the existing test suite.

---

# Objectives

Generate tests that

- Validate business behavior
- Cover success and failure cases
- Cover edge cases
- Maintain high code coverage
- Reuse existing fixtures
- Follow existing project conventions

---

# Existing Test Structure

Always place tests inside the appropriate directory.

```
tests/

tests/unit/

tests/integration/

tests/agent/

tests/rag/

tests/api/

tests/database/
```

Do not create duplicate test structures.

---

# Test Types

Choose the appropriate test type.

## Unit Tests

Use when testing

- Services
- Utilities
- Builders
- Nodes
- Prompt builders
- Repositories (mocked)

Mock all external dependencies.

---

## Integration Tests

Use when testing

- API endpoints
- Database repositories
- Retrieval pipeline
- Agent execution
- Chat streaming
- Authentication

Reuse project fixtures.

---

## End-to-End Tests

Use only when validating complete workflows across multiple layers.

---

# Test Design

Follow the Arrange–Act–Assert pattern.

Example

```python
# Arrange

# Act

# Assert
```

Keep each test focused on one behavior.

---

# Naming

Use descriptive names.

Examples

```
test_create_company_success

test_create_company_permission_denied

test_retrieval_returns_documents

test_generate_rejects_empty_query

test_chat_stream_returns_usage
```

Names should explain expected behavior.

---

# Fixtures

Reuse existing fixtures whenever possible.

Examples

- authed_client
- async_session
- seeded_tenant
- seeded_user
- seeded_organization
- retrieval_result

Avoid creating duplicate setup logic.

---

# Mocking

Mock external systems such as

- LLMProvider
- EmbeddingProvider
- RetrievalService
- VectorStore
- External APIs
- Storage providers

Do not mock the code being tested.

---

# AI Agent Tests

Validate

- AgentRunner
- AgentService
- GraphBuilder
- Nodes
- PromptBuilder
- State transitions
- Usage metadata
- Citations
- Error propagation

Test behavior rather than LangGraph internals.

---

# RAG Tests

Validate

- RetrievalService
- RAGChain
- Prompt generation
- Context creation
- Empty retrieval
- Provider failures
- Token usage
- Streaming

Mock the LLM provider where appropriate.

---

# API Tests

Verify

- Status codes
- Response schema
- Authentication
- Authorization
- Validation
- Streaming responses
- Error responses

Avoid relying on response ordering unless required.

---

# Database Tests

Validate

- CRUD operations
- Repository methods
- Tenant isolation
- Relationships
- Constraints
- Transactions

Ensure tests are isolated and repeatable.

---

# Edge Cases

Always consider

- Empty input
- Invalid input
- Missing permissions
- Missing resources
- Duplicate records
- Unexpected exceptions
- Multi-tenant boundaries

---

# Assertions

Assert observable behavior.

Prefer

```python
assert response.status_code == 200

assert result.response == expected

assert result.errors == []

assert usage.total_tokens > 0
```

Avoid asserting implementation details.

---

# Async Tests

Use

```python
@pytest.mark.asyncio
```

Await all async operations.

Avoid blocking calls.

---

# Coverage Expectations

Every new feature should include tests for

- Success
- Failure
- Validation
- Edge cases
- Permissions
- Error handling

Maintain high overall coverage.

---

# Output

When generating tests, provide

1. Test file location
2. Required fixtures
3. Mock dependencies
4. Complete test implementation
5. Any new helper utilities (if necessary)

---

# Things You Should NOT Do

Do not

- Duplicate fixtures
- Mock internal business logic
- Depend on external services
- Write flaky timing-based tests
- Test private implementation details
- Ignore edge cases

---

# Final Checklist

Before finishing, verify

- Tests follow project conventions.
- Existing fixtures are reused.
- External services are mocked.
- Success and failure cases are covered.
- Edge cases are tested.
- Async code is properly awaited.
- Assertions verify behavior.
- Tests are deterministic.
- Existing tests should continue to pass.
- The generated tests are production-ready.