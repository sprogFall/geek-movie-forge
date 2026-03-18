from __future__ import annotations

from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from packages.shared.contracts.assets import AssetResponse
from packages.shared.enums.model_capability import ModelCapability


class AssetSaveOptions(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    enabled: bool = False
    category: str | None = None
    name_prefix: str | None = None
    tags: list[str] = Field(default_factory=list)


class ImageGenerationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    provider_id: str = Field(min_length=1)
    model: str = Field(min_length=1)
    count: int = Field(default=1, ge=1, le=10)
    prompt: str | None = None
    preset_prompt: str | None = None
    save: AssetSaveOptions = Field(default_factory=AssetSaveOptions)
    options: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_prompt(self) -> Self:
        if not (self.prompt or self.preset_prompt):
            raise ValueError("prompt or preset_prompt is required")
        return self


class VideoGenerationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    provider_id: str = Field(min_length=1)
    model: str = Field(min_length=1)
    count: int = Field(default=1, ge=1, le=10)
    prompt: str | None = None
    preset_prompt: str | None = None
    image_material_asset_ids: list[str] = Field(default_factory=list)
    image_material_urls: list[str] = Field(default_factory=list)
    scene_prompt_asset_ids: list[str] = Field(default_factory=list)
    scene_prompt_texts: list[str] = Field(default_factory=list)
    save: AssetSaveOptions = Field(default_factory=AssetSaveOptions)
    options: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_prompt(self) -> Self:
        has_prompt = bool(self.prompt or self.preset_prompt)
        has_image_materials = bool(self.image_material_asset_ids or self.image_material_urls)
        has_draft_task = bool(str(self.options.get("draft_task_id") or "").strip())
        if not (has_prompt or has_image_materials or has_draft_task):
            raise ValueError(
                "prompt or preset_prompt is required when no image materials or draft_task_id are provided"
            )
        return self


class TextGenerationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    provider_id: str = Field(min_length=1)
    model: str = Field(min_length=1)
    task_type: str = Field(min_length=1)
    source_text: str = Field(min_length=1)
    prompt: str | None = None
    preset_prompt: str | None = None
    save: AssetSaveOptions = Field(default_factory=AssetSaveOptions)
    options: dict[str, Any] = Field(default_factory=dict)


class ImageGenerationPayload(BaseModel):
    provider_id: str
    model: str
    count: int
    prompt: str | None = None
    preset_prompt: str | None = None
    resolved_prompt: str = Field(min_length=1)
    options: dict[str, Any] = Field(default_factory=dict)


class VideoInputMaterial(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    kind: Literal["url", "base64"]
    value: str = Field(min_length=1)


class VideoGenerationPayload(BaseModel):
    provider_id: str
    model: str
    count: int
    prompt: str | None = None
    preset_prompt: str | None = None
    resolved_prompt: str | None = None
    image_materials: list[VideoInputMaterial] = Field(default_factory=list)
    image_material_urls: list[str] = Field(default_factory=list)
    image_material_base64: list[str] = Field(default_factory=list)
    scene_prompt_texts: list[str] = Field(default_factory=list)
    options: dict[str, Any] = Field(default_factory=dict)


class TextGenerationPayload(BaseModel):
    provider_id: str
    model: str
    task_type: str
    source_text: str
    prompt: str | None = None
    preset_prompt: str | None = None
    resolved_prompt: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)


class GeneratedMediaOutput(BaseModel):
    index: int
    url: str | None = None
    base64_data: str | None = None
    mime_type: str | None = None
    text: str | None = None
    cover_image_url: str | None = None
    duration_seconds: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProviderMediaGenerationResult(BaseModel):
    provider_request_id: str | None = None
    outputs: list[GeneratedMediaOutput] = Field(default_factory=list)


class ProviderTextGenerationResult(BaseModel):
    provider_request_id: str | None = None
    output_text: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MediaGenerationResponse(BaseModel):
    generation_id: str
    capability: ModelCapability
    provider_id: str
    model: str
    resolved_prompt: str
    provider_request_id: str | None = None
    outputs: list[GeneratedMediaOutput]
    saved_assets: list[AssetResponse] = Field(default_factory=list)


class TextGenerationResponse(BaseModel):
    generation_id: str
    capability: ModelCapability
    provider_id: str
    model: str
    task_type: str
    source_text: str
    resolved_prompt: str | None = None
    provider_request_id: str | None = None
    output_text: str
    saved_assets: list[AssetResponse] = Field(default_factory=list)
