from __future__ import annotations

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
from services.api.app.services.errors import (
    ConflictServiceError,
    NotFoundServiceError,
    ValidationServiceError,
)


class InMemoryProviderService:
    def __init__(self) -> None:
        self._providers: dict[str, ProviderRecord] = {}

    def create_provider(
        self,
        owner_id: str,
        payload: ProviderConfigCreateRequest,
    ) -> ProviderResponse:
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
        return provider.to_response()

    def update_provider(
        self,
        owner_id: str,
        provider_id: str,
        payload: ProviderConfigUpdateRequest,
    ) -> ProviderResponse:
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
            created_at=provider.created_at,
            updated_at=datetime.now(UTC),
        )
        self._providers[provider_id] = updated
        return updated.to_response()

    def list_providers(self, owner_id: str) -> ProviderListResponse:
        items = [
            provider.to_response()
            for provider in self._providers.values()
            if provider.owner_id == owner_id
        ]
        items.sort(key=lambda item: item.created_at)
        return ProviderListResponse(items=items)

    def get_provider(self, owner_id: str, provider_id: str) -> ProviderResponse | None:
        provider = self._providers.get(provider_id)
        if provider is None or provider.owner_id != owner_id:
            return None
        return provider.to_response() if provider else None

    def require_provider_record(self, owner_id: str, provider_id: str) -> ProviderRecord:
        provider = self._providers.get(provider_id)
        if provider is None or provider.owner_id != owner_id:
            raise NotFoundServiceError("Provider not found")
        return provider

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
        for provider in self._providers.values():
            if provider.owner_id != owner_id:
                continue
            if provider.name != name:
                continue
            if exclude_provider_id is not None and provider.provider_id == exclude_provider_id:
                continue
            raise ConflictServiceError("Provider name already exists")
