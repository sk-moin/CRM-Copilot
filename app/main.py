# app/main.py
"""CRM Copilot API application."""

from fastapi import FastAPI

# Import routers
from app.api.routes.company import router as company_router
from app.api.routes.contact import router as contact_router
from app.api.routes.opportunity import router as opportunity_router
from app.api.routes.task import router as task_router

app = FastAPI(
    title="CRM Copilot API",
    version="0.1.0",
    description="Multi-tenant CRM with AI‑powered copilot capabilities.",
)

# Health‑check endpoint
@app.get("/health")
async def health_check() -> dict[str, str]:
    """Simple health‑check endpoint."""
    return {"status": "ok"}

# Register routers
app.include_router(company_router, prefix="/companies", tags=["Companies"])
app.include_router(contact_router, prefix="/contacts", tags=["Contacts"])
app.include_router(opportunity_router, prefix="/opportunities", tags=["Opportunities"])
app.include_router(task_router, prefix="/tasks", tags=["Tasks"])
