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
