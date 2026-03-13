from fastapi import APIRouter, Depends, HTTPException, status

from packages.shared.contracts.auth import UserResponse
from services.api.app.dependencies.auth import get_current_user
from services.api.app.dependencies.services import get_project_service
from services.api.app.schemas.projects import (
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectResponse,
)
from services.api.app.services.project_service import InMemoryProjectService

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    project_service: InMemoryProjectService = Depends(get_project_service),
) -> ProjectResponse:
    return project_service.create_project(current_user.user_id, payload)


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    current_user: UserResponse = Depends(get_current_user),
    project_service: InMemoryProjectService = Depends(get_project_service),
) -> ProjectListResponse:
    return project_service.list_projects(current_user.user_id)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: UserResponse = Depends(get_current_user),
    project_service: InMemoryProjectService = Depends(get_project_service),
) -> ProjectResponse:
    project = project_service.get_project(current_user.user_id, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project

