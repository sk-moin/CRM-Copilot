# app/main.py
"""CRM Copilot API application."""

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request

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
from app.api.rate_limit import (
    AI_TIER,
    AUTH_TIER,
    DEFAULT_TIER,
    init_rate_limiter,
    reset_rate_limiter,
)
from app.guardrails.dependencies import get_guardrail_service
from app.observability.logging import configure_logging
from app.observability.metrics import metrics_snapshot, record_http_request
from app.observability.request_context import request_context
from dotenv import load_dotenv

load_dotenv()
configure_logging()
logger = logging.getLogger("crm_copilot.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    guardrails = get_guardrail_service()

    await guardrails.initialize()

    await init_rate_limiter()

    yield

    await guardrails.shutdown()

    # Release the Redis connection pool with the app, not at interpreter exit.
    from app.core.redis_client import reset_redis
    from app.jobs.queue import reset_queue

    await reset_redis()

    # The arq pool is a second, separate Redis connection pool held by the
    # enqueue side. Closing only the first leaked it for the process lifetime.
    await reset_queue()

    # The rate limiter holds a reference to the same client reset_redis()
    # just closed, not a pool of its own -- drop the reference, don't close
    # it again.
    await reset_rate_limiter()


app = FastAPI(
    title="CRM Copilot API",
    version="0.1.0",
    description="Multi-tenant CRM with AI‑powered copilot capabilities.",
    lifespan=lifespan,
)


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    start = time.perf_counter()
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    tenant_id = request.headers.get("x-tenant-id")
    org_id = request.headers.get("x-org-id")
    user_id = request.headers.get("x-user-id")

    with request_context(
        request_id=request_id,
        tenant_id=tenant_id,
        org_id=org_id,
        user_id=user_id,
    ):
        logger.info(
            "request.started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "tenant_id": tenant_id,
                "org_id": org_id,
                "user_id": user_id,
            },
        )
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 3)
            record_http_request(
                method=request.method,
                path=request.url.path,
                status_code=500,
                duration_ms=duration_ms,
            )
            logger.exception(
                "request.failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": 500,
                    "duration_ms": duration_ms,
                    "tenant_id": tenant_id,
                    "org_id": org_id,
                    "user_id": user_id,
                },
            )
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 3)
        record_http_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request.completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "tenant_id": tenant_id,
                "org_id": org_id,
                "user_id": user_id,
            },
        )
        return response


# Health-check endpoint
@app.get("/health")
async def health_check() -> dict[str, str]:
    """Simple health-check endpoint."""
    return {"status": "ok"}


@app.get("/metrics")
async def metrics() -> dict[str, object]:
    """Return the in-memory metrics snapshot for local observability."""
    return metrics_snapshot()

# Register routers
# Rate limiting is applied per router, not per handler. Three tiers:
# AUTH_TIER (strict, IP-keyed) on the unauthenticated login/register routes;
# AI_TIER (strict, tenant/user-keyed) on the routes that spend LLM or
# embedding budget; DEFAULT_TIER (generous, tenant/user-keyed) on everything
# else. document_router carries both AI_TIER and DEFAULT_TIER -- upload
# spends budget, status polling does not -- so its tiers are declared on the
# individual routes in app/api/routes/document.py instead of here.
_DEFAULT_TIER_DEPS = [Depends(DEFAULT_TIER)]

app.include_router(
    company_router,
    prefix="/api/v1/companies",
    tags=["Companies"],
    dependencies=_DEFAULT_TIER_DEPS,
)
app.include_router(
    contact_router,
    prefix="/api/v1/contacts",
    tags=["Contacts"],
    dependencies=_DEFAULT_TIER_DEPS,
)
app.include_router(
    opportunity_router,
    prefix="/api/v1/opportunities",
    tags=["Opportunities"],
    dependencies=_DEFAULT_TIER_DEPS,
)
app.include_router(
    task_router,
    prefix="/api/v1/tasks",
    tags=["Tasks"],
    dependencies=_DEFAULT_TIER_DEPS,
)
app.include_router(audit.router, prefix="/api/v1", dependencies=_DEFAULT_TIER_DEPS)
app.include_router(chat_router, prefix="/api/v1", dependencies=[Depends(AI_TIER)])
app.include_router(
    prompt_router, prefix="/api/v1", dependencies=_DEFAULT_TIER_DEPS
)
app.include_router(auth_router, prefix="/api/v1", dependencies=[Depends(AUTH_TIER)])
app.include_router(document_router, prefix="/api/v1")
app.include_router(rag_router, prefix="/api/v1", dependencies=[Depends(AI_TIER)])
app.include_router(
    retrieval_observability_router,
    prefix="/api/v1",
    dependencies=_DEFAULT_TIER_DEPS,
)
app.include_router(
    guardrails_router, prefix="/api/v1", dependencies=_DEFAULT_TIER_DEPS
)
app.include_router(
    actions_router, prefix="/api/v1", dependencies=_DEFAULT_TIER_DEPS
)