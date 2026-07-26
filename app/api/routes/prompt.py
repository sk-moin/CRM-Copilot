"""
API routes for Prompt Management.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.dependencies import get_prompt_repository, get_prompt_service
from app.api.schemas.prompt import (
    PromptCreate,
    PromptDetailResponse,
    PromptRenderRequest,
    PromptRenderResponse,
    PromptResponse,
    PromptUpdate,
    PromptVersionCreate,
    PromptVersionResponse,
)
from app.services.llm.prompt_service import PromptService
from packages.database.repositories.prompt_repository import PromptRepository

router = APIRouter(
    prefix="/prompts",
    tags=["Prompt Management"],
)


# ---------------------------------------------------------------------
# Prompt CRUD
# ---------------------------------------------------------------------


@router.get(
    "/",
    response_model=list[PromptResponse],
)
async def list_prompts(
    service: PromptService = Depends(get_prompt_service),
):
    return await service.list_prompts()


@router.post(
    "/",
    response_model=PromptResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_prompt(
    payload: PromptCreate,
    service: PromptService = Depends(get_prompt_service),
):
    return await service.create_prompt(**payload.model_dump())


@router.get(
    "/{prompt_id}",
    response_model=PromptDetailResponse,
)
async def get_prompt(
    prompt_id: UUID,
    service: PromptService = Depends(get_prompt_service),
):
    prompt = await service.get_prompt(prompt_id)

    if prompt is None:
        raise HTTPException(
            status_code=404,
            detail="Prompt not found.",
        )

    return prompt


@router.patch(
    "/{prompt_id}",
    response_model=PromptResponse,
)
async def update_prompt(
    prompt_id: UUID,
    payload: PromptUpdate,
    service: PromptService = Depends(get_prompt_service),
):
    prompt = await service.update_prompt(
        prompt_id,
        **payload.model_dump(exclude_unset=True),
    )

    if prompt is None:
        raise HTTPException(
            status_code=404,
            detail="Prompt not found.",
        )

    return prompt


@router.delete(
    "/{prompt_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_prompt(
    prompt_id: UUID,
    service: PromptService = Depends(get_prompt_service),
):
    await service.delete_prompt(prompt_id)

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )


# ---------------------------------------------------------------------
# Prompt Versions
# ---------------------------------------------------------------------


@router.get(
    "/{prompt_id}/versions",
    response_model=list[PromptVersionResponse],
)
async def list_prompt_versions(
    prompt_id: UUID,
    service: PromptService = Depends(get_prompt_service),
):
    return await service.list_versions(prompt_id)


@router.post(
    "/{prompt_id}/versions",
    response_model=PromptVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_prompt_version(
    prompt_id: UUID,
    payload: PromptVersionCreate,
    service: PromptService = Depends(get_prompt_service),
):
    return await service.create_version(
        prompt_id,
        **payload.model_dump(),
    )


@router.post(
    "/{prompt_id}/activate/{version_id}",
    response_model=PromptResponse,
)
async def activate_prompt_version(
    prompt_id: UUID,
    version_id: UUID,
    service: PromptService = Depends(get_prompt_service),
):
    prompt = await service.activate_version(
        prompt_id,
        version_id,
    )

    if prompt is None:
        raise HTTPException(
            status_code=404,
            detail="Prompt not found.",
        )

    return prompt


# ---------------------------------------------------------------------
# Prompt Rendering
# ---------------------------------------------------------------------


@router.post(
    "/{prompt_id}/render/",
    response_model=PromptRenderResponse,
)
async def render_prompt(
    prompt_id: UUID,
    payload: PromptRenderRequest,
    service: PromptService = Depends(get_prompt_service),
):
    try:
        rendered = await service.render_prompt(
            prompt_id,
            payload.variables,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    return PromptRenderResponse(
        prompt=rendered,
    )