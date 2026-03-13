from fastapi import Request

from services.api.app.services.asset_service import InMemoryAssetService
from services.api.app.services.generation_service import GenerationService
from services.api.app.services.project_service import InMemoryProjectService
from services.api.app.services.provider_service import InMemoryProviderService
from services.api.app.services.task_service import InMemoryTaskService


def get_task_service(request: Request) -> InMemoryTaskService:
    return request.app.state.task_service


def get_project_service(request: Request) -> InMemoryProjectService:
    return request.app.state.project_service


def get_provider_service(request: Request) -> InMemoryProviderService:
    return request.app.state.provider_service


def get_asset_service(request: Request) -> InMemoryAssetService:
    return request.app.state.asset_service


def get_generation_service(request: Request) -> GenerationService:
    return request.app.state.generation_service
