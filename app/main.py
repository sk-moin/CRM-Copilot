# app/main.py
"""CRM Copilot API application."""

from fastapi import FastAPI

# Import routers
from app.api.routes.company import router as company_router
from app.api.routes.contact import router as contact_router
from app.api.routes.opportunity import router as opportunity_router
from app.api.routes.task import router as task_router
from app.api.routes import audit
from app.api.routes.chat import router as chat_router
from app.api.routes.prompt import router as prompt_router
from app.api.routes.auth import router as auth_router
from app.api.routes.document import router as document_router
from app.api.routes.rag import router as rag_router
from app.api.routes.retrieval_observability import (
    router as retrieval_observability_router,
)
from app.api.routes.actions import router as actions_router
from app.api.routes.guardrails import (
    router as guardrails_router,
)
from contextlib import asynccontextmanager

from app.guardrails.dependencies import get_guardrail_service
from dotenv import load_dotenv

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    guardrails = get_guardrail_service()

    await guardrails.initialize()

    yield

    await guardrails.shutdown()

app = FastAPI(
    title="CRM Copilot API",
    version="0.1.0",
    description="Multi-tenant CRM with AI‑powered copilot capabilities.",
    lifespan=lifespan,
)

# Health‑check endpoint
@app.get("/health")
async def health_check() -> dict[str, str]:
    """Simple health‑check endpoint."""
    return {"status": "ok"}

# Register routers
app.include_router(company_router, prefix="/api/v1/companies", tags=["Companies"])
app.include_router(contact_router, prefix="/api/v1/contacts", tags=["Contacts"])
app.include_router(opportunity_router, prefix="/api/v1/opportunities", tags=["Opportunities"])
app.include_router(task_router, prefix="/api/v1/tasks", tags=["Tasks"])
app.include_router(audit.router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(prompt_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(document_router, prefix="/api/v1")
app.include_router(rag_router, prefix="/api/v1")
app.include_router(retrieval_observability_router, prefix="/api/v1")
app.include_router(guardrails_router, prefix="/api/v1")
app.include_router(actions_router, prefix="/api/v1")