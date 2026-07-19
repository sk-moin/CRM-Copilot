---
name: add-api-endpoint
description: Create a FastAPI API endpoint following the CRM Copilot architecture. Endpoints should remain thin, delegate business logic to services, use dependency injection, and return Pydantic schemas.
---

# Add API Endpoint

## Goal

Implement a production-ready FastAPI endpoint that follows the CRM Copilot architecture.

API endpoints should be responsible only for HTTP concerns while delegating all business logic to the service layer.

---

# Responsibilities

This skill is responsible for:

- Creating FastAPI routes
- Request validation
- Response serialization
- Dependency injection
- Authentication
- Authorization dependencies
- Calling services
- Returning HTTP responses

This skill is NOT responsible for:

- Business logic
- Database queries
- Repository operations
- Workflow orchestration
- Data persistence

---

# Project Structure

API routes are located in

```
app/api/routes/
```

Schemas are located in

```
app/api/schemas/
```

Dependencies are located in

```
app/api/dependencies.py
```

Examples

```
company.py
contact.py
task.py
chat.py
retrieval.py
```

---

# Router

Always create a router.

Example

```python
router = APIRouter(
    prefix="/companies",
    tags=["Companies"],
)
```

Use meaningful prefixes and tags.

---

# Dependency Injection

Never instantiate services manually.

Always use

```python
Depends(...)
```

Example

```python
service: CompanyService = Depends(
    get_company_service,
)
```

---

# Authentication

Protected endpoints must require

```python
current_user = Depends(get_current_user)
```

Never trust IDs provided by the client.

Use the authenticated user whenever possible.

---

# Service Layer

Endpoints should immediately delegate work to a service.

Example

```python
company = await service.create_company(...)
```

Business logic must never exist inside the route.

---

# Request Validation

Use Pydantic request schemas.

Example

```python
CompanyCreateRequest
```

Never accept raw dictionaries.

---

# Response Models

Always return response schemas.

Example

```python
response_model=CompanyResponse
```

Avoid returning ORM models directly.

---

# HTTP Status Codes

Use appropriate status codes.

Examples

```
200 OK

201 Created

204 No Content

400 Bad Request

401 Unauthorized

403 Forbidden

404 Not Found

409 Conflict

422 Validation Error
```

---

# Error Handling

Convert domain exceptions into HTTP exceptions.

Example

```python
raise HTTPException(
    status_code=404,
    detail="Company not found.",
)
```

Repositories and services should never raise HTTPException.

---

# Async

Endpoints should always be asynchronous.

Example

```python
@router.post(...)
async def create_company(...):
```

---

# Pagination

List endpoints should support pagination when appropriate.

Use existing project pagination conventions.

Avoid custom pagination logic.

---

# Filtering

Accept filters through query parameters.

Example

```python
status

search

page

page_size
```

Keep filtering logic inside services.

---

# Path Parameters

Use UUID types whenever possible.

Example

```python
company_id: UUID
```

Avoid using string IDs.

---

# Query Parameters

Use FastAPI Query when validation is required.

Example

```python
page: int = Query(
    default=1,
    ge=1,
)
```

---

# File Uploads

If the endpoint accepts files,

Use

```python
UploadFile
```

Do not manually parse multipart requests.

---

# Streaming

Streaming endpoints should return

```python
StreamingResponse
```

Example

```
text/event-stream
```

Keep streaming logic delegated to services.

---

# Documentation

Each endpoint should include

- summary
- docstring
- response model
- status code

Keep descriptions concise.

---

# Naming

Route functions

```
create_company()

update_company()

delete_company()

list_companies()

get_company()
```

Use clear REST-style naming.

---

# Output Requirements

Generated code should include

- imports
- router
- endpoint
- dependency injection
- request schema
- response schema
- status codes
- type hints
- docstrings

No placeholders.

No TODO comments.

No business logic.

---

# Code Style

Preferred

```python
result = await service.create(...)
return CompanyResponse.model_validate(result)
```

Avoid deeply nested conditionals.

Keep endpoints thin.

---

# Validation Checklist

Before finishing verify

- Uses APIRouter
- Uses dependency injection
- Uses request schema
- Uses response schema
- No business logic
- Async endpoint
- Correct status codes
- Authentication applied
- Proper type hints
- Production-ready implementation
```