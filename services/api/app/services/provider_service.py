from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, sessionmaker

from packages.db.models import ProviderRow
from packages.shared.contracts.providers import (
    ProviderConfigCreateRequest,
    ProviderConfigUpdateRequest,
    ProviderListResponse,
    ProviderModelConfig,
    ProviderRecord,
    ProviderResponse,
    ProviderRoutes,
)
from packages.shared.enums.model_capability import ModelCapability
from services.api.app.services.errors import (
    ConflictServiceError,
    NotFoundServiceError,
    ValidationServiceError,
)

_BUILTIN_PROVIDER_DEFS = (
    {
        "key": "volcengine_ark",
        "name": "Volcengine Ark",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "adapter_type": "volcengine_ark",
        "api_key_env": "VOLCENGINE_ARK_API_KEY",
        "models": [
            ProviderModelConfig(
                model="doubao-seedance-1-5-pro-251215",
                capabilities=[ModelCapability.VIDEO],
                label="Seedance 1.5 Pro",
            ),
        ],
        "routes": {
            "video": {"path": "/contents/generations/tasks", "timeout_seconds": 300.0},
        },
    },
    {
        "key": "modelscope",
        "name": "ModelScope",
        "base_url": "https://api-inference.modelscope.cn",
        "adapter_type": "modelscope",
        "models": [
            ProviderModelConfig(
                model="Qwen/Qwen2.5-7B-Instruct",
                capabilities=[ModelCapability.TEXT],
                label="Qwen2.5 7B Instruct",
            ),
            ProviderModelConfig(
                model="Qwen/Qwen-Image-2512",
                capabilities=[ModelCapability.IMAGE],
                label="Qwen Image 2512",
            ),
        ],
        "routes": {
            "text": {"path": "/v1/chat/completions", "timeout_seconds": 60.0},
            "image": {"path": "/v1/images/generations", "timeout_seconds": 120.0},
            "video": {"path": "/video/generations", "timeout_seconds": 600.0},
        },
    },
)


from packages.shared.utils import parse_timestamp as _parse_timestamp


def _serialize_models(models: list[ProviderModelConfig]) -> list[dict]:
    return [item.model_dump(mode="json") for item in models]


def _serialize_routes(routes: ProviderRoutes) -> dict:
    return routes.model_dump(mode="json")


class InMemoryProviderService:
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create_provider(
        self,
        owner_id: str,
        payload: ProviderConfigCreateRequest,
    ) -> ProviderResponse:
        timestamp = datetime.now(UTC).isoformat()
        provider_id = f"provider_{uuid4().hex[:12]}"

        with self._session_factory() as session:
            self._ensure_builtin_providers(session, owner_id)
            self._ensure_unique_name(session, owner_id, payload.name)
            session.add(
                ProviderRow(
                    provider_id=provider_id,
                    owner_id=owner_id,
                    name=payload.name,
                    base_url=str(payload.base_url),
                    api_key=payload.api_key,
                    adapter_type=payload.adapter_type,
                    models_json=_serialize_models(payload.models),
                    routes_json=_serialize_routes(payload.routes),
                    is_builtin=False,
                    created_at=timestamp,
                    updated_at=timestamp,
                )
            )
            session.commit()

        return ProviderRecord(
            provider_id=provider_id,
            owner_id=owner_id,
            name=payload.name,
            base_url=payload.base_url,
            api_key=payload.api_key,
            adapter_type=payload.adapter_type,
            models=payload.models,
            routes=payload.routes,
            created_at=_parse_timestamp(timestamp),
            updated_at=_parse_timestamp(timestamp),
        ).to_response()

    def update_provider(
        self,
        owner_id: str,
        provider_id: str,
        payload: ProviderConfigUpdateRequest,
    ) -> ProviderResponse:
        with self._session_factory() as session:
            self._ensure_builtin_providers(session, owner_id)
            provider = self._require_provider_row(session, owner_id, provider_id)
            if payload.name is not None and payload.name != provider.name:
                self._ensure_unique_name(
                    session,
                    owner_id,
                    payload.name,
                    exclude_provider_id=provider_id,
                )

            provider.name = payload.name or provider.name
            provider.base_url = str(payload.base_url) if payload.base_url is not None else provider.base_url
            provider.api_key = payload.api_key if payload.api_key is not None else provider.api_key
            provider.models_json = (
                _serialize_models(payload.models) if payload.models is not None else provider.models_json
            )
            provider.routes_json = (
                _serialize_routes(payload.routes) if payload.routes is not None else provider.routes_json
            )
            provider.updated_at = datetime.now(UTC).isoformat()
            session.commit()
            session.refresh(provider)
            return _to_record(provider).to_response()

    def list_providers(self, owner_id: str) -> ProviderListResponse:
        with self._session_factory() as session:
            self._ensure_builtin_providers(session, owner_id)
            rows = session.scalars(
                select(ProviderRow)
                .where(ProviderRow.owner_id == owner_id)
                .order_by(desc(ProviderRow.is_builtin), ProviderRow.created_at, ProviderRow.name)
            ).all()
        return ProviderListResponse(items=[_to_record(row).to_response() for row in rows])

    def get_provider(self, owner_id: str, provider_id: str) -> ProviderResponse | None:
        with self._session_factory() as session:
            self._ensure_builtin_providers(session, owner_id)
            row = session.get(ProviderRow, provider_id)
            if row is None or row.owner_id != owner_id:
                return None
            return _to_record(row).to_response()

    def require_provider_record(self, owner_id: str, provider_id: str) -> ProviderRecord:
        with self._session_factory() as session:
            self._ensure_builtin_providers(session, owner_id)
            return _to_record(self._require_provider_row(session, owner_id, provider_id))

    def delete_provider(self, owner_id: str, provider_id: str) -> None:
        with self._session_factory() as session:
            self._ensure_builtin_providers(session, owner_id)
            provider = self._require_provider_row(session, owner_id, provider_id)
            if provider.is_builtin:
                raise ConflictServiceError("Built-in provider cannot be deleted")
            session.delete(provider)
            session.commit()

    def ensure_model_capability(
        self,
        owner_id: str,
        provider_id: str,
        model: str,
        capability: ModelCapability,
    ) -> tuple[ProviderRecord, ProviderModelConfig]:
        provider = self.require_provider_record(owner_id, provider_id)
        model_config = next((item for item in provider.models if item.model == model), None)
        if model_config is None:
            raise NotFoundServiceError("Model not found in provider config")
        if capability not in model_config.capabilities:
            raise ValidationServiceError(f"Model does not support {capability.value} generation")
        return provider, model_config

    def _ensure_unique_name(
        self,
        session: Session,
        owner_id: str,
        name: str,
        exclude_provider_id: str | None = None,
    ) -> None:
        row = session.scalar(
            select(ProviderRow).where(
                ProviderRow.owner_id == owner_id,
                ProviderRow.name == name,
            )
        )
        if row is None:
            return
        if exclude_provider_id is not None and row.provider_id == exclude_provider_id:
            return
        raise ConflictServiceError("Provider name already exists")

    def _ensure_builtin_providers(self, session: Session, owner_id: str) -> None:
        changed = False
        for item in _BUILTIN_PROVIDER_DEFS:
            provider_id = _builtin_provider_id(owner_id, item["key"])
            row = session.get(ProviderRow, provider_id)
            desired_api_key = _builtin_api_key(item)
            desired_models = _serialize_models(item["models"])
            desired_routes = item["routes"]
            if row is None:
                timestamp = datetime.now(UTC).isoformat()
                session.add(
                    ProviderRow(
                        provider_id=provider_id,
                        owner_id=owner_id,
                        name=item["name"],
                        base_url=item["base_url"],
                        api_key=desired_api_key,
                        adapter_type=item["adapter_type"],
                        models_json=desired_models,
                        routes_json=desired_routes,
                        is_builtin=True,
                        created_at=timestamp,
                        updated_at=timestamp,
                    )
                )
                changed = True
                continue

            # Built-in providers are user-editable after initialization.
            # Preserve stored API keys, models, routes, and names on later reads.
            if not row.is_builtin:
                row.is_builtin = True
                row.updated_at = datetime.now(UTC).isoformat()
                changed = True
        if changed:
            session.commit()

    @staticmethod
    def _require_provider_row(session: Session, owner_id: str, provider_id: str) -> ProviderRow:
        row = session.get(ProviderRow, provider_id)
        if row is None or row.owner_id != owner_id:
            raise NotFoundServiceError("Provider not found")
        return row


def _to_record(row: ProviderRow) -> ProviderRecord:
    return ProviderRecord(
        provider_id=row.provider_id,
        owner_id=row.owner_id,
        name=row.name,
        base_url=row.base_url,
        api_key=row.api_key,
        adapter_type=row.adapter_type,
        models=[ProviderModelConfig.model_validate(item) for item in row.models_json],
        routes=ProviderRoutes.model_validate(row.routes_json or {}),
        is_builtin=row.is_builtin,
        created_at=_parse_timestamp(row.created_at),
        updated_at=_parse_timestamp(row.updated_at),
    )


def _builtin_provider_id(owner_id: str, key: str) -> str:
    return f"provider_builtin_{key}_{owner_id}"


def _builtin_api_key(item: dict) -> str:
    env_name = item.get("api_key_env")
    if not env_name:
        return ""
    return os.getenv(env_name, "").strip()
