from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import uuid4

from packages.shared.contracts.providers import (
    ProviderConfigCreateRequest,
    ProviderConfigUpdateRequest,
    ProviderListResponse,
    ProviderModelConfig,
    ProviderRecord,
    ProviderResponse,
)
from packages.shared.enums.model_capability import ModelCapability
from services.api.app.core.store import JsonFileStore
from services.api.app.services.errors import (
    ConflictServiceError,
    NotFoundServiceError,
    ValidationServiceError,
)

_NAMESPACE = "providers"

_BUILTIN_PROVIDER_DEFS = (
    {
        "key": "modelscope",
        "name": "魔搭 ModelScope",
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
            "video": {"path": "/video/generations", "timeout_seconds": 60.0},
        },
    },
)


class InMemoryProviderService:
    def __init__(self, *, store: JsonFileStore | None = None) -> None:
        self._providers: dict[str, ProviderRecord] = {}
        self._store = store
        self._load()

    def create_provider(
        self,
        owner_id: str,
        payload: ProviderConfigCreateRequest,
    ) -> ProviderResponse:
        self._ensure_builtin_providers(owner_id)
        self._ensure_unique_name(owner_id, payload.name)
        timestamp = datetime.now(UTC)
        provider = ProviderRecord(
            provider_id=f"provider_{uuid4().hex[:12]}",
            owner_id=owner_id,
            name=payload.name,
            base_url=payload.base_url,
            api_key=payload.api_key,
            adapter_type=payload.adapter_type,
            models=payload.models,
            routes=payload.routes,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self._providers[provider.provider_id] = provider
        self._persist()
        return provider.to_response()

    def update_provider(
        self,
        owner_id: str,
        provider_id: str,
        payload: ProviderConfigUpdateRequest,
    ) -> ProviderResponse:
        self._ensure_builtin_providers(owner_id)
        provider = self.require_provider_record(owner_id, provider_id)
        if payload.name is not None and payload.name != provider.name:
            self._ensure_unique_name(
                owner_id,
                payload.name,
                exclude_provider_id=provider_id,
            )

        updated = ProviderRecord(
            provider_id=provider.provider_id,
            owner_id=provider.owner_id,
            name=payload.name or provider.name,
            base_url=payload.base_url or provider.base_url,
            api_key=payload.api_key or provider.api_key,
            adapter_type=provider.adapter_type,
            models=payload.models or provider.models,
            routes=payload.routes or provider.routes,
            is_builtin=provider.is_builtin,
            created_at=provider.created_at,
            updated_at=datetime.now(UTC),
        )
        self._providers[provider_id] = updated
        self._persist()
        return updated.to_response()

    def list_providers(self, owner_id: str) -> ProviderListResponse:
        self._ensure_builtin_providers(owner_id)
        items = [
            provider.to_response()
            for provider in self._providers.values()
            if provider.owner_id == owner_id
        ]
        items.sort(key=lambda item: (not item.is_builtin, item.created_at, item.name))
        return ProviderListResponse(items=items)

    def get_provider(self, owner_id: str, provider_id: str) -> ProviderResponse | None:
        self._ensure_builtin_providers(owner_id)
        provider = self._providers.get(provider_id)
        if provider is None or provider.owner_id != owner_id:
            return None
        return provider.to_response() if provider else None

    def require_provider_record(self, owner_id: str, provider_id: str) -> ProviderRecord:
        self._ensure_builtin_providers(owner_id)
        provider = self._providers.get(provider_id)
        if provider is None or provider.owner_id != owner_id:
            raise NotFoundServiceError("Provider not found")
        return provider

    def delete_provider(self, owner_id: str, provider_id: str) -> None:
        provider = self.require_provider_record(owner_id, provider_id)
        if provider.is_builtin:
            raise ConflictServiceError("Built-in provider cannot be deleted")
        del self._providers[provider_id]
        self._persist()

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
        owner_id: str,
        name: str,
        exclude_provider_id: str | None = None,
    ) -> None:
        self._ensure_builtin_providers(owner_id)
        for provider in self._providers.values():
            if provider.owner_id != owner_id:
                continue
            if provider.name != name:
                continue
            if exclude_provider_id is not None and provider.provider_id == exclude_provider_id:
                continue
            raise ConflictServiceError("Provider name already exists")

    def _ensure_builtin_providers(self, owner_id: str) -> None:
        changed = False
        for item in _BUILTIN_PROVIDER_DEFS:
            provider_id = _builtin_provider_id(owner_id, item["key"])
            if provider_id in self._providers:
                continue
            timestamp = datetime.now(UTC)
            self._providers[provider_id] = ProviderRecord(
                provider_id=provider_id,
                owner_id=owner_id,
                name=item["name"],
                base_url=item["base_url"],
                api_key="",
                adapter_type=item["adapter_type"],
                models=item["models"],
                routes=item["routes"],
                is_builtin=True,
                created_at=timestamp,
                updated_at=timestamp,
            )
            changed = True
        if changed:
            self._persist()

    def _persist(self) -> None:
        if self._store is None:
            return
        data = {k: v.model_dump(mode="json") for k, v in self._providers.items()}
        self._store.save(_NAMESPACE, data)

    def _load(self) -> None:
        if self._store is None:
            return
        data = self._store.load(_NAMESPACE)
        if data is None:
            return
        for key, value in data.items():
            try:
                self._providers[key] = ProviderRecord(**value)
            except Exception:
                logging.getLogger(__name__).warning(
                    "Skipping corrupt provider entry %s", key
                )


def _builtin_provider_id(owner_id: str, key: str) -> str:
    return f"provider_builtin_{key}_{owner_id}"
