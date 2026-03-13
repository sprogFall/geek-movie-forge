from fastapi import APIRouter, Depends, HTTPException, status

from packages.shared.contracts.auth import UserResponse
from services.api.app.dependencies.auth import get_current_user
from services.api.app.dependencies.services import get_task_service
from services.api.app.schemas.tasks import TaskCreateRequest, TaskResponse
from services.api.app.services.task_service import InMemoryTaskService

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreateRequest,
    _user: UserResponse = Depends(get_current_user),
    task_service: InMemoryTaskService = Depends(get_task_service),
) -> TaskResponse:
    return task_service.create_task(payload)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    _user: UserResponse = Depends(get_current_user),
    task_service: InMemoryTaskService = Depends(get_task_service),
) -> TaskResponse:
    task = task_service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task
