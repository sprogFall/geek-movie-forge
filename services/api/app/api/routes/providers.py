from fastapi import APIRouter, Depends, HTTPException, status

from packages.shared.contracts.auth import UserResponse
from services.api.app.dependencies.auth import get_current_user
from services.api.app.dependencies.services import get_provider_service
from services.api.app.schemas.providers import (
    ProviderConfigCreateRequest,
    ProviderConfigUpdateRequest,
    ProviderListResponse,
    ProviderResponse,
)
from services.api.app.services.provider_service import InMemoryProviderService

router = APIRouter(prefix="/api/v1/providers", tags=["providers"])


@router.post(
    "",
    response_model=ProviderResponse,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
)
async def create_provider(
    payload: ProviderConfigCreateRequest,
    _user: UserResponse = Depends(get_current_user),
    provider_service: InMemoryProviderService = Depends(get_provider_service),
) -> ProviderResponse:
    return provider_service.create_provider(payload)


@router.put(
    "/{provider_id}",
    response_model=ProviderResponse,
    response_model_exclude_none=True,
)
async def update_provider(
    provider_id: str,
    payload: ProviderConfigUpdateRequest,
    _user: UserResponse = Depends(get_current_user),
    provider_service: InMemoryProviderService = Depends(get_provider_service),
) -> ProviderResponse:
    return provider_service.update_provider(provider_id, payload)


@router.get("", response_model=ProviderListResponse, response_model_exclude_none=True)
async def list_providers(
    _user: UserResponse = Depends(get_current_user),
    provider_service: InMemoryProviderService = Depends(get_provider_service),
) -> ProviderListResponse:
    return provider_service.list_providers()


@router.get(
    "/{provider_id}",
    response_model=ProviderResponse,
    response_model_exclude_none=True,
)
async def get_provider(
    provider_id: str,
    _user: UserResponse = Depends(get_current_user),
    provider_service: InMemoryProviderService = Depends(get_provider_service),
) -> ProviderResponse:
    provider = provider_service.get_provider(provider_id)
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    return provider
