from __future__ import annotations

from datetime import datetime
from typing import Literal, Self

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, model_validator

from packages.shared.enums.model_capability import ModelCapability

ProviderAdapterType = Literal["generic_json", "modelscope"]


class ProviderModelConfig(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    model: str = Field(min_length=1)
    capabilities: list[ModelCapability] = Field(min_length=1)
    label: str | None = None

    @model_validator(mode="after")
    def validate_capabilities(self) -> Self:
        if len(set(self.capabilities)) != len(self.capabilities):
            raise ValueError("Duplicate capability is not allowed")
        return self


class ProviderEndpointConfig(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    path: str = Field(min_length=1)
    timeout_seconds: float = Field(default=60.0, gt=0)


def _default_text_endpoint() -> ProviderEndpointConfig:
    return ProviderEndpointConfig(path="/text/generations")


def _default_image_endpoint() -> ProviderEndpointConfig:
    return ProviderEndpointConfig(path="/image/generations")


def _default_video_endpoint() -> ProviderEndpointConfig:
    return ProviderEndpointConfig(path="/video/generations")


class ProviderRoutes(BaseModel):
    text: ProviderEndpointConfig = Field(default_factory=_default_text_endpoint)
    image: ProviderEndpointConfig = Field(default_factory=_default_image_endpoint)
    video: ProviderEndpointConfig = Field(default_factory=_default_video_endpoint)


class ProviderConfigCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1)
    base_url: AnyHttpUrl
    api_key: str = Field(min_length=1)
    adapter_type: ProviderAdapterType = "generic_json"
    models: list[ProviderModelConfig] = Field(min_length=1)
    routes: ProviderRoutes = Field(default_factory=ProviderRoutes)

    @model_validator(mode="after")
    def validate_models(self) -> Self:
        model_names = [item.model for item in self.models]
        if len(set(model_names)) != len(model_names):
            raise ValueError("Duplicate model is not allowed")
        return self


class ProviderConfigUpdateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1)
    base_url: AnyHttpUrl | None = None
    api_key: str | None = Field(default=None, min_length=1)
    models: list[ProviderModelConfig] | None = Field(default=None, min_length=1)
    routes: ProviderRoutes | None = None

    @model_validator(mode="after")
    def validate_update(self) -> Self:
        if (
            self.name is None
            and self.base_url is None
            and self.api_key is None
            and self.models is None
            and self.routes is None
        ):
            raise ValueError("At least one field must be provided")
        if self.models is not None:
            model_names = [item.model for item in self.models]
            if len(set(model_names)) != len(model_names):
                raise ValueError("Duplicate model is not allowed")
        return self


class ProviderResponse(BaseModel):
    provider_id: str
    name: str
    base_url: AnyHttpUrl
    api_key_masked: str
    adapter_type: ProviderAdapterType
    models: list[ProviderModelConfig]
    routes: ProviderRoutes
    is_builtin: bool = False
    created_at: datetime
    updated_at: datetime


class ProviderListResponse(BaseModel):
    items: list[ProviderResponse]


class ProviderRecord(BaseModel):
    provider_id: str
    owner_id: str
    name: str
    base_url: AnyHttpUrl
    api_key: str
    adapter_type: ProviderAdapterType = "generic_json"
    models: list[ProviderModelConfig]
    routes: ProviderRoutes = Field(default_factory=ProviderRoutes)
    is_builtin: bool = False
    created_at: datetime
    updated_at: datetime

    def to_response(self) -> ProviderResponse:
        return ProviderResponse(
            provider_id=self.provider_id,
            name=self.name,
            base_url=self.base_url,
            api_key_masked=_mask_api_key(self.api_key),
            adapter_type=self.adapter_type,
            models=self.models,
            routes=self.routes,
            is_builtin=self.is_builtin,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


def _mask_api_key(api_key: str) -> str:
    if len(api_key) <= 6:
        return "*" * len(api_key)
    return f"{api_key[:3]}{'*' * (len(api_key) - 6)}{api_key[-3:]}"
