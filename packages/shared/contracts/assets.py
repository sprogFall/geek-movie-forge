from __future__ import annotations

from datetime import datetime
from typing import Any, Self

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, model_validator

from packages.shared.enums.asset_origin import AssetOrigin
from packages.shared.enums.asset_type import AssetType


class AssetCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    asset_type: AssetType
    category: str = Field(min_length=1)
    name: str = Field(min_length=1)
    content_url: AnyHttpUrl | None = None
    content_text: str | None = None
    content_base64: str | None = None
    mime_type: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    provider_id: str | None = None
    model: str | None = None

    @model_validator(mode="after")
    def validate_content(self) -> Self:
        if not any((self.content_url, self.content_text, self.content_base64)):
            raise ValueError("At least one asset content field is required")
        return self


class AssetResponse(BaseModel):
    asset_id: str
    asset_type: AssetType
    category: str
    name: str
    origin: AssetOrigin
    content_url: AnyHttpUrl | None = None
    content_text: str | None = None
    content_base64: str | None = None
    mime_type: str | None = None
    tags: list[str]
    metadata: dict[str, Any]
    provider_id: str | None = None
    model: str | None = None
    created_at: datetime


class AssetListResponse(BaseModel):
    items: list[AssetResponse]
