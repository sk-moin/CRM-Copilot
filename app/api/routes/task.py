# app/api/routes/task.py
"""FastAPI router for Task CRUD operations.

Maps service exceptions to HTTP status codes:
* EntityNotFoundError → 404
* BusinessRuleViolationError → 400
"""

from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_task_service
from app.api.schemas.task import TaskCreate, TaskUpdate, TaskResponse
from app.services.task_service import TaskService
from app.services.exceptions import EntityNotFoundError, BusinessRuleViolationError

router = APIRouter()

@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    try:
        task = await service.create_task(**payload.model_dump())
        return task
    except BusinessRuleViolationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

@router.get("/{task_id}", response_model=TaskResponse)
async def read_task(
    task_id: UUID,
    service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    try:
        return await service.get_task(str(task_id))
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

@router.get("/", response_model=List[TaskResponse])
async def list_tasks(
    service: TaskService = Depends(get_task_service),
) -> List[TaskResponse]:
    return await service.list_tasks()

@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    payload: TaskUpdate,
    service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    try:
        return await service.update_task(
            str(task_id), **payload.model_dump(exclude_unset=True)
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except BusinessRuleViolationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
