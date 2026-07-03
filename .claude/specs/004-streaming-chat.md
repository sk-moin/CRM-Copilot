# Spec 004 — Streaming Chat

## Goal

Implement the conversational interface for CRM Copilot. This specification introduces persistent conversations, immutable message history, streaming LLM responses using Server-Sent Events (SSE), and an extensible provider abstraction that future AI capabilities (RAG, Tool Calling, Agents, GraphRAG, Voice) will build upon.

---

# Context

## Current Architecture

```text
FastAPI
    ↓
Router
    ↓
Service
    ↓
Repository
    ↓
Async SQLAlchemy
    ↓
PostgreSQL
```

## Multi-tenancy

* All database queries **must** be tenant-scoped.
* Conversation ownership is enforced at both the repository and service layers.

## Current Project Status

```text
Spec 000 — Database Foundations     ✅
Spec 001 — Authentication & RBAC    ✅
Spec 002 — CRM Core                 ✅
Spec 003 — Audit & Activity         ✅
```

Current test suite:

```text
73 passing tests
0 failures
```

## Lessons from Spec 003

* Use singular table names (`tenant`, `organization`, `user`, `audit_log`)
* Reuse the recursive JSON-safe serializer for all JSONB fields
* Integration tests must share the same DB session (`override get_db`)
* Repository pattern uses instance-based initialization (`session + tenant_id`)
* Snapshot builders remain the centralized serialization mechanism
* Import `func` from `sqlalchemy` when using `func.gen_random_uuid()` or `func.now()`

---

# High-Level Objectives

* Persistent conversations
* Immutable message history
* Streaming LLM responses (SSE)
* Provider abstraction (`LLMProvider`)
* Conversation management (CRUD)
* Cancellation support
* Usage tracking
* Audit integration
* Foundation for future AI specifications

---

# Scope

## Included

* Conversation model
* Message model
* Alembic migration
* Conversation repository
* Message repository
* LLMProvider abstraction
* OpenAIProvider implementation
* StreamingManager
* ConversationService
* ChatService
* PromptBuilder
* Streaming API
* Conversation management API
* Message history endpoint
* Unit & integration tests

## Not Included

* Feedback / message rating (Spec 008)
* RAG retrieval (Spec 005)
* Tool calling (Spec 006)
* Agents (Spec 006)
* Memory (Spec 034)
* Voice
* WebSocket streaming
* File attachments
* Multi-model gateway (Spec 030)

---

# Design Principles

## Conversation Ownership

Each conversation belongs to:

```text
tenant_id (required)
organization_id (optional)
user_id (required)
```

Users may only access conversations within their tenant.

---

## Message Immutability

Messages are append-only.

Messages are never edited or deleted.

Soft deleting a conversation hides it from normal queries but retains messages for audit purposes.

---

## Provider Independence

The service layer must never depend on provider-specific SDK objects.

All providers implement a common `LLMProvider` interface.

---

## Streaming

Streaming uses **Server-Sent Events (SSE)**.

Reasons:

* One-way communication
* Native FastAPI support
* Simpler infrastructure
* Compatible with proxies/load balancers

---

## Audit Integration

Chat operations must generate audit events.

Minimum events:

* `conversation.created`
* `conversation.updated`
* `conversation.deleted`
* `message.created`
* `assistant.generated`

Audit events are emitted by `ChatService` and `ConversationService` using the `AuditService` from Spec 003.

---

## JSON Serialization

All JSONB columns must reuse the recursive serializer introduced in Spec 003.

Supported conversions:

* UUID → string
* Decimal → string
* datetime → ISO 8601
* Enum → value

---

## Error Handling

Provider errors must be caught and converted to SSE error events:

* `openai.RateLimitError` → `event: error
data: {"type":"rate_limit","message":"Too many requests"}`
* `openai.AuthenticationError` → `event: error
data: {"type":"auth","message":"Provider authentication failed"}`
* `openai.APIConnectionError` → `event: error
data: {"type":"connection","message":"Unable to reach provider"}`
* Generic `Exception` → `event: error
data: {"type":"internal","message":"Generation failed"}`

The stream closes immediately after the error event.

---

# Phase Breakdown

## Phase 4A — Models & Migration

Deliverables:

* Conversation model
* Message model
* Alembic migration
* Database indexes

---

## Phase 4B — Repository Layer

Deliverables:

* ConversationRepository
* MessageRepository
* Tenant-scoped queries

---

## Phase 4C — Service Layer

Deliverables:

* ConversationService
* ChatService
* StreamingManager
* PromptBuilder
* LLMProvider
* OpenAIProvider

---

## Phase 4D — API

Deliverables:

* Streaming endpoint
* Conversation CRUD
* Message history endpoint

---

## Phase 4E — Testing

Deliverables:

* Repository tests
* Service tests
* Streaming tests
* Integration tests
* Tenant isolation tests
* Cancellation tests

Target:

```text
100+ passing tests
```

---

# Data Models

## Conversation

**File**

```text
app/models/conversation.py
```

```python
from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text, UUID as PGUUID, func
from sqlalchemy.dialects.postgresql import JSONB
from enum import Enum

from packages.database.models.base import Base


class ConversationStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class Conversation(Base):
    __tablename__ = "conversation"

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())

    tenant_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
    )

    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=True,
    )

    user_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
    )

    title = Column(String(255), nullable=True)

    status = Column(
        String(20),
        nullable=False,
        default="active",
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        Index("ix_conversation_tenant_user", "tenant_id", "user_id"),
        Index("ix_conversation_tenant_status", "tenant_id", "status"),
        Index("ix_conversation_created_at", "created_at"),
    )
```

### Conversation Rules

* Soft delete only.
* Title is set by `ChatService` when first user message arrives (first 100 characters trimmed).
* Messages are never removed during soft delete.
* All queries exclude `deleted_at IS NOT NULL`.

---

## Message

**File**

```text
app/models/message.py
```

```python
from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, Index, Integer, String, Text, UUID as PGUUID, func
from sqlalchemy.dialects.postgresql import JSONB
from enum import Enum

from packages.database.models.base import Base


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class Message(Base):
    __tablename__ = "message"

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())

    conversation_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("conversation.id", ondelete="CASCADE"),
        nullable=False,
    )

    tenant_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
    )

    role = Column(
        SAEnum(MessageRole, name="message_role"),
        nullable=False,
    )

    content = Column(Text, nullable=False)

    model = Column(String(100), nullable=True)

    prompt_tokens = Column(Integer, nullable=True)

    completion_tokens = Column(Integer, nullable=True)

    total_tokens = Column(Integer, nullable=True)

    latency_ms = Column(Integer, nullable=True)

    finish_reason = Column(String(50), nullable=True)

    message_metadata = Column(JSONB, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_message_conversation", "conversation_id", "created_at"),
        Index("ix_message_tenant", "tenant_id"),
    )
```

### Message Rules

* `content` uses `Text`
* `message_metadata` avoids SQLAlchemy's reserved `metadata`
* Messages are immutable
* History is always ordered by `created_at ASC`
* Messages do not store `organization_id` directly; org-scoped queries join through `conversation`

---

# Repository Layer

Repositories follow the existing project pattern:

* Initialize with `AsyncSession` and `tenant_id`
* Perform persistence only
* No business logic
* No authorization logic
* No provider-specific code

---

## ConversationRepository

**File**

```text
app/repositories/conversation_repository.py
```

### Required Methods

```python
async def list_for_user(
    user_id: UUID,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
)

async def get_by_id(conversation_id: UUID)

async def create(conversation: Conversation)

async def update(conversation: Conversation)

async def soft_delete(conversation_id: UUID)
```

### Requirements

* Automatically filter by `tenant_id`
* Exclude soft-deleted conversations (`deleted_at IS NULL`)
* Support pagination
* Order by `updated_at DESC`

---

## MessageRepository

**File**

```text
app/repositories/message_repository.py
```

### Required Methods

```python
async def list_for_conversation(
    conversation_id: UUID,
    limit: int = 100,
    offset: int = 0,
)

async def create(message: Message)

async def get_by_id(message_id: UUID)
```

### Requirements

* Automatically filter by `tenant_id`
* Return messages ordered by `created_at ASC`
* No update methods
* No delete methods

---

# Service Layer

---

## LLM Provider

**Files**

```text
app/services/llm/base.py
app/services/llm/openai_provider.py
```

### TokenUsage Dataclass

```python
from dataclasses import dataclass

@dataclass
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
```

### StreamChunk Dataclass

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class StreamChunk:
    token: Optional[str] = None
    finish_reason: Optional[str] = None
    usage: Optional[TokenUsage] = None
```

### LLMProvider Abstract Base Class

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional

class LLMProvider(ABC):
    @abstractmethod
    async def stream(
        self,
        messages: list[dict],
        model: Optional[str] = None,
    ) -> AsyncIterator[StreamChunk]:
        """Yield tokens as they arrive from the LLM."""
        ...

    @abstractmethod
    async def complete(
        self,
        messages: list[dict],
        model: Optional[str] = None,
    ) -> str:
        """Return full response (non-streaming, for background jobs)."""
        ...
```

---

## OpenAIProvider

Responsibilities:

* Authenticate using `OPENAI_API_KEY`
* Stream tokens via `AsyncIterator[StreamChunk]`
* Return completion metadata
* Hide OpenAI SDK objects

Configuration (read from application settings):

```text
OPENAI_API_KEY      (required)
OPENAI_MODEL        (default: "gpt-4o")
OPENAI_TIMEOUT      (default: 60)
OPENAI_MAX_RETRIES  (default: 3)
```

No model names should be hardcoded.

Error handling:

* Catch `openai.RateLimitError`, `openai.AuthenticationError`, `openai.APIConnectionError`, `openai.APIError`
* Convert to `StreamChunk` with `finish_reason="error"` or raise provider-agnostic exception

---

## PromptBuilder

**File**

```text
app/services/llm/prompt_builder.py
```

Responsibilities:

* Build provider messages
* Include system prompt
* Include conversation history
* Append latest user message

Prompt order:

```text
System

↓

Conversation History

↓

Latest User Message
```

Future specs may inject:

* RAG context
* Memory
* Tool results
* Agent reasoning

without modifying ChatService.

---

## ConversationService

**File**

```text
app/services/conversation_service.py
```

Responsibilities:

* Create conversations
* Retrieve conversations
* List conversations
* Update title
* Archive conversations
* Soft delete conversations
* Enforce ownership
* Emit audit events via `AuditService`

---

## ChatService

**File**

```text
app/services/chat_service.py
```

Responsibilities:

* Validate ownership
* Create conversation when needed (set title from first 100 chars of user message)
* Persist user message
* Load history
* Build prompt via `PromptBuilder`
* Call `LLMProvider.stream()`
* Collect streamed tokens
* Persist assistant message (with full content, model, tokens, latency, metadata)
* Store token usage
* Emit audit events via `AuditService`
* Measure latency using `time.perf_counter()`

ChatService must remain independent of:

* FastAPI
* SSE formatting
* OpenAI SDK

---

## StreamingManager

**File**

```text
app/services/streaming_manager.py
```

Responsibilities:

* Convert ChatService output into SSE events
* Detect client disconnects via `await request.is_disconnected()`
* Handle cancellation (break loop, signal cleanup)
* Emit completion events
* Emit error events
* Format SSE payloads consistently

StreamingManager owns all HTTP streaming behavior.

---

# API Layer

## Schemas

**File**

```text
app/schemas/chat.py
```

### ChatRequest

```python
class ChatRequest(BaseModel):
    message: str
    conversation_id: UUID | None = None
```

---

### ConversationResponse

```python
class ConversationResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    organization_id: UUID | None
    user_id: UUID
    title: str | None
    status: str
    created_at: datetime
    updated_at: datetime
```

---

### MessageResponse

```python
class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str

    model: str | None

    prompt_tokens: int | None

    completion_tokens: int | None

    total_tokens: int | None

    latency_ms: int | None

    finish_reason: str | None

    message_metadata: dict | None

    created_at: datetime
```

---

# Router

**File**

```text
app/api/routes/chat.py
```

## Endpoints

```http
POST /chat/stream
```

Request:

```json
{
  "message": "...",
  "conversation_id": null
}
```

Response:

```text
text/event-stream
```

---

```http
GET /conversations
```

Returns all active conversations for the current user.

---

```http
GET /conversations/{conversation_id}
```

Returns a single conversation.

---

```http
PATCH /conversations/{conversation_id}
```

Supports:

* title update
* archive (status = "archived")

---

```http
DELETE /conversations/{conversation_id}
```

Soft delete only.

---

```http
GET /conversations/{conversation_id}/messages
```

Returns ordered message history.

---

# Streaming Events

The SSE endpoint emits the following events:

### start

```text
event: start
data: {"conversation_id":"..."}
```

---

### token

```text
event: token
data: Hello
```

---

### usage

```json
{
  "prompt_tokens": 24,
  "completion_tokens": 81,
  "total_tokens": 105,
  "latency_ms": 640,
  "model": "gpt-4.1"
}
```

---

### done

```json
{
  "conversation_id": "...",
  "message_id": "...",
  "finish_reason": "stop"
}
```

---

### error

Returned when generation fails.

```json
{
  "type": "rate_limit",
  "message": "Too many requests"
}
```

The stream closes immediately after the error event.

---

# Dependency Injection

Modify:

```text
app/api/dependencies.py
```

Add:

```python
get_conversation_service()

get_chat_service()

get_llm_provider()
```

The provider instance should be created from application settings and injected into `ChatService`.

Provider configuration is read from the application settings module (e.g., `app.core.config.Settings`).

`OPENAI_API_KEY` is required; if missing, the application should raise on startup or return 503 from the streaming endpoint.

---

# Testing Requirements

## Unit Tests

ConversationRepository:

* create
* get_by_id
* list_for_user
* update
* soft_delete

MessageRepository:

* create
* get_by_id
* list_for_conversation

ConversationService:

* create conversation
* archive
* delete
* ownership validation

ChatService:

* create conversation automatically
* persist user message
* stream tokens
* persist assistant message
* provider error handling
* cancellation handling

---

## Integration Tests

* Streaming endpoint returns SSE
* New conversation created when `conversation_id` is null
* Existing conversation reused
* Messages persisted after completion
* Conversations listed correctly
* Message history returned in chronological order
* Conversation archived successfully
* Soft delete hides conversations
* Audit events generated

---

## Adversarial Tests

* Cross-tenant access denied
* Cross-user access denied
* Soft-deleted conversations excluded
* Provider failure handled gracefully
* Client cancellation stops generation

Target:

```text
100+ passing tests
```

Minimum:

```text
27 new tests
```

---

# Files to Create

```text
app/models/conversation.py
app/models/message.py

app/repositories/conversation_repository.py
app/repositories/message_repository.py

app/services/llm/base.py
app/services/llm/openai_provider.py
app/services/llm/prompt_builder.py

app/services/conversation_service.py
app/services/chat_service.py
app/services/streaming_manager.py

app/schemas/chat.py
app/api/routes/chat.py

alembic/versions/xxx_add_conversation_message.py
```

---

# Files to Modify

```text
app/api/dependencies.py
app/api/router.py

app/models/__init__.py
app/repositories/__init__.py
```

---

# Acceptance Criteria

* Conversation model supports soft delete
* Message model supports immutable history
* Migration creates all tables and indexes
* ConversationRepository implements CRUD + soft delete with `deleted_at IS NULL` filter
* MessageRepository implements create and list operations (no update/delete)
* LLMProvider abstraction is provider-independent with `StreamChunk` and `TokenUsage`
* OpenAIProvider streams responses via `AsyncIterator[StreamChunk]`
* PromptBuilder constructs provider-ready messages
* ChatService orchestrates the complete chat lifecycle including title auto-generation
* StreamingManager formats SSE events and handles client disconnects
* `/chat/stream` streams responses successfully
* Conversation management endpoints function correctly
* Message history endpoint returns ordered messages
* Audit events are generated for conversation and message lifecycle
* Tenant isolation enforced at repository level
* Existing 73 tests continue passing
* Total test count exceeds 100
* Schema supports future RAG, Tool Calling, Agents, and Voice features without additional database migrations

---

# Out of Scope

Future specifications will implement:

* Spec 005 — RAG & Document Retrieval
* Spec 006 — Tool Calling & AI Agent
* Spec 007 — Human Approval Workflows
* Spec 008 — Feedback & Message Rating
* Spec 030 — Multi-Model Gateway
* Voice Streaming
* WebSocket Transport
* File Attachments
* Long-Term Memory
* Real-Time Collaboration

The schema introduced in Spec 004 must support those future capabilities without requiring additional database migrations.
