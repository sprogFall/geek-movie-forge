from fastapi import APIRouter, Depends, HTTPException, status

from packages.shared.contracts.auth import UserResponse
from packages.shared.enums.task_status import TaskStatus
from services.api.app.dependencies.auth import get_current_user
from services.api.app.dependencies.services import get_task_service
from services.api.app.schemas.tasks import TaskCreateRequest, TaskListResponse, TaskResponse
from services.api.app.services.task_service import InMemoryTaskService

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    task_service: InMemoryTaskService = Depends(get_task_service),
) -> TaskResponse:
    return task_service.create_task(current_user.user_id, payload)


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    project_id: str | None = None,
    status: TaskStatus | None = None,
    current_user: UserResponse = Depends(get_current_user),
    task_service: InMemoryTaskService = Depends(get_task_service),
) -> TaskListResponse:
    return task_service.list_tasks(
        owner_id=current_user.user_id,
        project_id=project_id,
        status=status,
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    current_user: UserResponse = Depends(get_current_user),
    task_service: InMemoryTaskService = Depends(get_task_service),
) -> TaskResponse:
    task = task_service.get_task(current_user.user_id, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task
