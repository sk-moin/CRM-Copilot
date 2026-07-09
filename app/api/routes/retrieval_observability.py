"""API routes for Retrieval Observability."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import (
    get_retrieval_trace_service,
    get_retrieved_chunk_service,
)

from app.api.schemas.retrieval_trace import (
    RetrievalTraceListResponse,
    RetrievalTraceRead,
)
from app.api.schemas.retrieved_chunk import (
    RetrievedChunkListResponse,
)
from app.services.retrieval_trace_service import RetrievalTraceService
from app.services.retrieved_chunk_service import RetrievedChunkService

router = APIRouter(
    prefix="/retrieval",
    tags=["Retrieval Observability"],
)


@router.get(
    "/traces",
    response_model=RetrievalTraceListResponse,
)
async def list_retrieval_traces(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: RetrievalTraceService = Depends(
        get_retrieval_trace_service,
    ),
) -> RetrievalTraceListResponse:
    """List retrieval traces for the current tenant."""

    traces = await service.list_by_tenant(
        limit=limit,
        offset=offset,
    )

    return RetrievalTraceListResponse(
        items=traces,
        total=len(traces),
    )


@router.get(
    "/traces/{trace_id}",
    response_model=RetrievalTraceRead,
)
async def get_retrieval_trace(
    trace_id: UUID,
    service: RetrievalTraceService = Depends(
        get_retrieval_trace_service,
    ),
) -> RetrievalTraceRead:
    """Retrieve a single retrieval trace."""

    trace = await service.get_trace(trace_id)

    if trace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Retrieval trace not found.",
        )

    return trace


@router.get(
    "/traces/{trace_id}/chunks",
    response_model=RetrievedChunkListResponse,
)
async def get_retrieved_chunks(
    trace_id: UUID,
    service: RetrievedChunkService = Depends(
        get_retrieved_chunk_service,
    ),
) -> RetrievedChunkListResponse:
    """Retrieve all chunks for a retrieval trace."""

    chunks = await service.get_by_trace(trace_id)

    return RetrievedChunkListResponse(
        items=chunks,
        total=len(chunks),
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=RetrievalTraceListResponse,
)
async def get_conversation_traces(
    conversation_id: UUID,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: RetrievalTraceService = Depends(
        get_retrieval_trace_service,
    ),
) -> RetrievalTraceListResponse:
    """Retrieve all retrieval traces for a conversation."""

    traces = await service.list_by_conversation(
        conversation_id=conversation_id,
        limit=limit,
        offset=offset,
    )

    return RetrievalTraceListResponse(
        items=traces,
        total=len(traces),
    )