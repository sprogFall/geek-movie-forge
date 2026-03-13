from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from packages.shared.contracts.assets import AssetCreateRequest, AssetListResponse, AssetResponse
from packages.shared.enums.asset_origin import AssetOrigin
from packages.shared.enums.asset_type import AssetType
from services.api.app.services.errors import NotFoundServiceError


class InMemoryAssetService:
    def __init__(self) -> None:
        self._assets: dict[str, AssetResponse] = {}

    def create_asset(
        self,
        payload: AssetCreateRequest,
        *,
        origin: AssetOrigin = AssetOrigin.MANUAL,
    ) -> AssetResponse:
        asset = AssetResponse(
            asset_id=f"asset_{uuid4().hex[:12]}",
            asset_type=payload.asset_type,
            category=payload.category,
            name=payload.name,
            origin=origin,
            content_url=payload.content_url,
            content_text=payload.content_text,
            content_base64=payload.content_base64,
            mime_type=payload.mime_type,
            tags=payload.tags,
            metadata=payload.metadata,
            provider_id=payload.provider_id,
            model=payload.model,
            created_at=datetime.now(UTC),
        )
        self._assets[asset.asset_id] = asset
        return asset

    def list_assets(
        self,
        *,
        asset_type: AssetType | None = None,
        category: str | None = None,
        provider_id: str | None = None,
        origin: AssetOrigin | None = None,
    ) -> AssetListResponse:
        items = list(self._assets.values())
        if asset_type is not None:
            items = [item for item in items if item.asset_type == asset_type]
        if category is not None:
            items = [item for item in items if item.category == category]
        if provider_id is not None:
            items = [item for item in items if item.provider_id == provider_id]
        if origin is not None:
            items = [item for item in items if item.origin == origin]
        items.sort(key=lambda item: item.created_at)
        return AssetListResponse(items=items)

    def get_asset(self, asset_id: str) -> AssetResponse | None:
        return self._assets.get(asset_id)

    def require_asset(self, asset_id: str) -> AssetResponse:
        asset = self._assets.get(asset_id)
        if asset is None:
            raise NotFoundServiceError("Asset not found")
        return asset
