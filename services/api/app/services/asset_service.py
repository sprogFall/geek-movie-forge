from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import uuid4

from packages.shared.contracts.assets import AssetCreateRequest, AssetListResponse, AssetResponse
from packages.shared.enums.asset_origin import AssetOrigin
from packages.shared.enums.asset_type import AssetType
from services.api.app.core.store import JsonFileStore
from services.api.app.services.errors import NotFoundServiceError

_NAMESPACE = "assets"


class InMemoryAssetService:
    def __init__(self, *, store: JsonFileStore | None = None) -> None:
        self._assets: dict[str, AssetResponse] = {}
        self._asset_owners: dict[str, str] = {}
        self._store = store
        self._load()

    def create_asset(
        self,
        owner_id: str,
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
        self._asset_owners[asset.asset_id] = owner_id
        self._persist()
        return asset

    def list_assets(
        self,
        *,
        owner_id: str,
        asset_type: AssetType | None = None,
        category: str | None = None,
        provider_id: str | None = None,
        origin: AssetOrigin | None = None,
    ) -> AssetListResponse:
        items = [
            asset
            for asset_id, asset in self._assets.items()
            if self._asset_owners.get(asset_id) == owner_id
        ]
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

    def get_asset(self, owner_id: str, asset_id: str) -> AssetResponse | None:
        asset = self._assets.get(asset_id)
        if asset is None or self._asset_owners.get(asset_id) != owner_id:
            return None
        return asset

    def require_asset(self, owner_id: str, asset_id: str) -> AssetResponse:
        asset = self.get_asset(owner_id, asset_id)
        if asset is None:
            raise NotFoundServiceError("Asset not found")
        return asset

    def update_asset(
        self,
        owner_id: str,
        asset_id: str,
        *,
        tags: list[str] | None = None,
        content_text: str | None = None,
    ) -> AssetResponse:
        asset = self.require_asset(owner_id, asset_id)
        if content_text is not None and asset.asset_type != AssetType.TEXT:
            raise ValueError("Only text assets can update content_text")

        updated = AssetResponse(
            asset_id=asset.asset_id,
            asset_type=asset.asset_type,
            category=asset.category,
            name=asset.name,
            origin=asset.origin,
            content_url=asset.content_url,
            content_text=content_text if content_text is not None else asset.content_text,
            content_base64=asset.content_base64,
            mime_type=asset.mime_type,
            tags=tags if tags is not None else asset.tags,
            metadata=asset.metadata,
            provider_id=asset.provider_id,
            model=asset.model,
            created_at=asset.created_at,
        )
        self._assets[asset_id] = updated
        self._persist()
        return updated

    def delete_asset(self, owner_id: str, asset_id: str) -> None:
        asset = self.require_asset(owner_id, asset_id)
        del self._assets[asset.asset_id]
        self._asset_owners.pop(asset.asset_id, None)
        self._persist()

    def _persist(self) -> None:
        if self._store is None:
            return
        data = {
            "assets": {k: v.model_dump(mode="json") for k, v in self._assets.items()},
            "owners": self._asset_owners,
        }
        self._store.save(_NAMESPACE, data)

    def _load(self) -> None:
        if self._store is None:
            return
        data = self._store.load(_NAMESPACE)
        if data is None:
            return
        for key, value in data.get("assets", {}).items():
            try:
                self._assets[key] = AssetResponse(**value)
            except Exception:
                logging.getLogger(__name__).warning(
                    "Skipping corrupt asset entry %s", key
                )
        self._asset_owners = data.get("owners", {})
