"""
Guardrails API routes.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_user
from app.api.schemas.guardrails import (
    GuardrailGenerateRequest,
    GuardrailGenerateResponse,
)
from app.guardrails.dependencies import get_guardrail_service
from app.guardrails.exceptions import (
    GuardrailInputBlockedError,
    GuardrailProviderError,
)
from app.guardrails.service import GuardrailService
from packages.database.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/guardrails",
    tags=["Guardrails"],
)


@router.get(
    "/health",
)
async def health(
    service: GuardrailService = Depends(get_guardrail_service),
    current_user: User = Depends(get_current_user),
):
    # health_check lives on the provider, not the service.
    return await service.provider.health_check()


@router.post(
    "/test",
    response_model=GuardrailGenerateResponse,
)
async def test_guardrails(
    request: GuardrailGenerateRequest,
    service: GuardrailService = Depends(
        get_guardrail_service,
    ),
    current_user: User = Depends(get_current_user),
):
    """
    Execute a real request through NeMo Guardrails.
    """

    # A blocked message is the main thing this endpoint exists to demonstrate,
    # so it must be a normal response, not a 500. Mirrors the RAG route.
    try:
        response = await service.generate(
            messages=[
                {
                    "role": "user",
                    "content": request.message,
                }
            ],
        )

    except GuardrailInputBlockedError:
        return GuardrailGenerateResponse(
            response=service.input_fallback_message,
            provider=service.provider.__class__.__name__,
            initialized=service.initialized,
        )

    except GuardrailProviderError as exc:
        logger.warning("guardrails.test.provider_error", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The guardrail provider is unavailable.",
        ) from exc

    return GuardrailGenerateResponse(
        response=response,
        provider=service.provider.__class__.__name__,
        initialized=service.initialized,
    )