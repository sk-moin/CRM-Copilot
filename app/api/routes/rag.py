"""
app/api/routes/rag.py

Retrieval-Augmented Generation API endpoints.
"""

from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from app.api.dependencies import (
    get_current_user,
    get_rag_service,
)
from app.api.schemas.rag import (
    RAGQueryRequest,
    RAGQueryResponse,
)
from app.rag.service import RAGService
from packages.database.models import User

router = APIRouter(
    prefix="/rag",
    tags=["RAG"],
)


@router.post(
    "/query",
    response_model=RAGQueryResponse,
    status_code=status.HTTP_200_OK,
)
async def query_rag(
    request: RAGQueryRequest,
    rag_service: RAGService = Depends(
        get_rag_service,
    ),
    current_user: User = Depends(
        get_current_user,
    ),
) -> RAGQueryResponse:
    """
    Execute a Retrieval-Augmented Generation query.
    """

    try:
        response = await rag_service.ask(
            conversation_id=request.conversation_id,
            query=request.query,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
            document_id=request.document_id,
        )

        return RAGQueryResponse(
            answer=response.answer,
            retrieved_chunks=len(response.documents),
            similarity_scores=response.similarity_scores,
            sources=[
                {
                    "chunk_id": document.metadata.get("chunk_id"),
                    "document_id": document.metadata.get("document_id"),
                    "chunk_index": document.metadata.get("chunk_index"),
                    "title": document.metadata.get("title"),
                    "filename": document.metadata.get("filename"),
                    "score": score,
                }
                for document, score in zip(
                    response.documents,
                    response.similarity_scores,
                )
            ],
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc