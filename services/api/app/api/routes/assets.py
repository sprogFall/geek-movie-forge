from fastapi import APIRouter, Depends, HTTPException, status

from packages.shared.contracts.auth import UserResponse
from packages.shared.enums.asset_origin import AssetOrigin
from packages.shared.enums.asset_type import AssetType
from services.api.app.dependencies.auth import get_current_user
from services.api.app.dependencies.services import get_asset_service
from services.api.app.schemas.assets import AssetCreateRequest, AssetListResponse, AssetResponse
from services.api.app.services.asset_service import InMemoryAssetService

router = APIRouter(prefix="/api/v1/assets", tags=["assets"])


@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(
    payload: AssetCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    asset_service: InMemoryAssetService = Depends(get_asset_service),
) -> AssetResponse:
    return asset_service.create_asset(current_user.user_id, payload)


@router.get("", response_model=AssetListResponse)
async def list_assets(
    asset_type: AssetType | None = None,
    category: str | None = None,
    provider_id: str | None = None,
    origin: AssetOrigin | None = None,
    current_user: UserResponse = Depends(get_current_user),
    asset_service: InMemoryAssetService = Depends(get_asset_service),
) -> AssetListResponse:
    return asset_service.list_assets(
        owner_id=current_user.user_id,
        asset_type=asset_type,
        category=category,
        provider_id=provider_id,
        origin=origin,
    )


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: str,
    current_user: UserResponse = Depends(get_current_user),
    asset_service: InMemoryAssetService = Depends(get_asset_service),
) -> AssetResponse:
    asset = asset_service.get_asset(current_user.user_id, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return asset
