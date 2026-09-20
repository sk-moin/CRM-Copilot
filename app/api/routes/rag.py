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

from app.guardrails.dependencies import get_guardrail_service
from app.guardrails.exceptions import GuardrailInputBlockedError
from app.guardrails.service import GuardrailService
import logging

from app.api.dependencies import (
    get_current_user,
    get_rag_service,
)
from app.api.schemas.rag import (
    RAGQueryRequest,
    RAGQueryResponse,
)
from app.rag.rag_service import RAGService
from packages.database.models import User

logger = logging.getLogger(__name__)

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
    guardrail_service: GuardrailService = Depends(
        get_guardrail_service,
    ),
) -> RAGQueryResponse:
    """
    Execute a Retrieval-Augmented Generation query.

    This endpoint returns generated text to a user, so it runs the same
    input and output rails as the chat path. Without them it was a second,
    unguarded way to reach the model.
    """

    try:
        guardrail_service.validate_input(request.query)
    except GuardrailInputBlockedError:
        return RAGQueryResponse(
            answer=guardrail_service.input_fallback_message,
            retrieved_chunks=0,
            sources=[],
        )

    try:
        response = await rag_service.ask(
            conversation_id=request.conversation_id,
            query=request.query,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
            document_id=request.document_id,
        )

        answer = await guardrail_service.validate_output(
            response.answer,
            user_input=request.query,
        )

        return RAGQueryResponse(
            answer=answer,
            retrieved_chunks=len(response.documents),
            sources=[
                {
                    "chunk_id": document.metadata.get("chunk_id"),
                    "document_id": document.metadata.get("document_id"),
                    "chunk_index": document.metadata.get("chunk_index"),
                    "title": document.metadata.get("title"),
                    "filename": document.metadata.get("filename"),
                    "content": document.page_content,
                    "similarity_score": score,
                }
                for document, score in zip(
                    response.documents,
                    response.similarity_scores,
                )
            ],
        )

    except Exception as exc:
        # Log the detail; do not return it. Internal exception text can carry
        # query fragments, model names and provider messages.
        logger.exception("rag.query.failed")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate a response.",
        ) from exc