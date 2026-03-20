from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from packages.db.models import AssetRow
from packages.shared.contracts.assets import AssetCreateRequest, AssetListResponse, AssetResponse
from packages.shared.enums.asset_origin import AssetOrigin
from packages.shared.enums.asset_type import AssetType
from services.api.app.services.errors import NotFoundServiceError


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value)


class InMemoryAssetService:
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create_asset(
        self,
        owner_id: str,
        payload: AssetCreateRequest,
        *,
        origin: AssetOrigin = AssetOrigin.MANUAL,
    ) -> AssetResponse:
        created_at = datetime.now(UTC).isoformat()
        asset_id = f"asset_{uuid4().hex[:12]}"

        with self._session_factory() as session:
            session.add(
                AssetRow(
                    asset_id=asset_id,
                    owner_id=owner_id,
                    asset_type=payload.asset_type.value,
                    category=payload.category,
                    name=payload.name,
                    origin=origin.value,
                    content_url=str(payload.content_url) if payload.content_url is not None else None,
                    content_text=payload.content_text,
                    content_base64=payload.content_base64,
                    mime_type=payload.mime_type,
                    tags_json=list(payload.tags),
                    metadata_json=dict(payload.metadata),
                    provider_id=payload.provider_id,
                    model=payload.model,
                    created_at=created_at,
                )
            )
            session.commit()

        return AssetResponse(
            asset_id=asset_id,
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
            created_at=_parse_timestamp(created_at),
        )

    def list_assets(
        self,
        *,
        owner_id: str,
        asset_type: AssetType | None = None,
        category: str | None = None,
        provider_id: str | None = None,
        origin: AssetOrigin | None = None,
    ) -> AssetListResponse:
        stmt = select(AssetRow).where(AssetRow.owner_id == owner_id)
        if asset_type is not None:
            stmt = stmt.where(AssetRow.asset_type == asset_type.value)
        if category is not None:
            stmt = stmt.where(AssetRow.category == category)
        if provider_id is not None:
            stmt = stmt.where(AssetRow.provider_id == provider_id)
        if origin is not None:
            stmt = stmt.where(AssetRow.origin == origin.value)
        stmt = stmt.order_by(AssetRow.created_at)

        with self._session_factory() as session:
            rows = session.scalars(stmt).all()
        return AssetListResponse(items=[_to_response(row) for row in rows])

    def get_asset(self, owner_id: str, asset_id: str) -> AssetResponse | None:
        with self._session_factory() as session:
            row = session.get(AssetRow, asset_id)
            if row is None or row.owner_id != owner_id:
                return None
            return _to_response(row)

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
        with self._session_factory() as session:
            row = session.get(AssetRow, asset_id)
            if row is None or row.owner_id != owner_id:
                raise NotFoundServiceError("Asset not found")
            if content_text is not None and row.asset_type != AssetType.TEXT.value:
                raise ValueError("Only text assets can update content_text")

            if tags is not None:
                row.tags_json = tags
            if content_text is not None:
                row.content_text = content_text
            session.commit()
            session.refresh(row)
            return _to_response(row)

    def delete_asset(self, owner_id: str, asset_id: str) -> None:
        with self._session_factory() as session:
            row = session.get(AssetRow, asset_id)
            if row is None or row.owner_id != owner_id:
                raise NotFoundServiceError("Asset not found")
            session.delete(row)
            session.commit()


def _to_response(row: AssetRow) -> AssetResponse:
    return AssetResponse(
        asset_id=row.asset_id,
        asset_type=AssetType(row.asset_type),
        category=row.category,
        name=row.name,
        origin=AssetOrigin(row.origin),
        content_url=row.content_url,
        content_text=row.content_text,
        content_base64=row.content_base64,
        mime_type=row.mime_type,
        tags=row.tags_json or [],
        metadata=row.metadata_json or {},
        provider_id=row.provider_id,
        model=row.model,
        created_at=_parse_timestamp(row.created_at),
    )
