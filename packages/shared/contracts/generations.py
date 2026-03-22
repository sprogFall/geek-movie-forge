from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from packages.shared.contracts.assets import AssetResponse
from packages.shared.enums.model_capability import ModelCapability
from packages.shared.contracts.call_logs import TokenUsage as _CallLogTokenUsage  # noqa: F401


class AssetSaveOptions(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    enabled: bool = False
    category: str | None = None
    name_prefix: str | None = None
    tags: list[str] = Field(default_factory=list)


class TokenUsage(BaseModel):
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)


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
        has_scene_prompt_materials = bool(self.scene_prompt_asset_ids or self.scene_prompt_texts)
        has_image_materials = bool(self.image_material_asset_ids or self.image_material_urls)
        has_draft_task = bool(str(self.options.get("draft_task_id") or "").strip())
        if not (
            has_prompt or has_scene_prompt_materials or has_image_materials or has_draft_task
        ):
            raise ValueError(
                "prompt, preset_prompt, or scene prompt text is required when no image materials or draft_task_id are provided"
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


class VideoSegmentPlan(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    segment_index: int = Field(ge=1)
    title: str = Field(min_length=1)
    duration_seconds: int = Field(ge=1, le=120)
    visual_prompt: str = Field(min_length=1)
    narration_text: str = Field(min_length=1)
    use_previous_segment_last_frame: bool = False


class MultiVideoPlanRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    provider_id: str = Field(min_length=1)
    model: str = Field(min_length=1)
    prompt: str | None = None
    preset_prompt: str | None = None
    total_duration_seconds: int = Field(ge=5, le=600)
    segment_duration_seconds: int = Field(ge=5, le=120)
    scene_prompt_asset_ids: list[str] = Field(default_factory=list)
    scene_prompt_texts: list[str] = Field(default_factory=list)
    options: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_durations(self) -> Self:
        if self.segment_duration_seconds > self.total_duration_seconds:
            raise ValueError("segment_duration_seconds must be <= total_duration_seconds")
        if not (
            self.prompt
            or self.preset_prompt
            or self.scene_prompt_asset_ids
            or self.scene_prompt_texts
        ):
            raise ValueError("prompt, preset_prompt, or scene prompt text is required")
        return self


class MultiVideoPlanResponse(BaseModel):
    plan_id: str
    provider_id: str
    model: str
    prompt: str
    resolved_prompt: str
    total_duration_seconds: int
    segment_duration_seconds: int
    segment_count: int
    provider_request_id: str | None = None
    usage: TokenUsage | None = None
    segments: list[VideoSegmentPlan] = Field(default_factory=list)


class MultiVideoGenerationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    provider_id: str = Field(min_length=1)
    model: str = Field(min_length=1)
    prompt: str | None = None
    preset_prompt: str | None = None
    segments: list[VideoSegmentPlan] = Field(min_length=1)
    image_material_asset_ids: list[str] = Field(default_factory=list)
    image_material_urls: list[str] = Field(default_factory=list)
    scene_prompt_asset_ids: list[str] = Field(default_factory=list)
    scene_prompt_texts: list[str] = Field(default_factory=list)
    save: AssetSaveOptions = Field(default_factory=AssetSaveOptions)
    options: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_segment_frame_links(self) -> Self:
        for index, segment in enumerate(self.segments):
            if index == 0 and segment.use_previous_segment_last_frame:
                raise ValueError(
                    "first segment cannot enable use_previous_segment_last_frame"
                )
        return self


class MultiVideoSegmentRegenerationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    provider_id: str = Field(min_length=1)
    model: str = Field(min_length=1)
    prompt: str | None = None
    preset_prompt: str | None = None
    segment: VideoSegmentPlan
    image_material_asset_ids: list[str] = Field(default_factory=list)
    image_material_urls: list[str] = Field(default_factory=list)
    scene_prompt_asset_ids: list[str] = Field(default_factory=list)
    scene_prompt_texts: list[str] = Field(default_factory=list)
    previous_segment_last_frame_url: str | None = None
    previous_segment_last_frame_base64: str | None = None
    save: AssetSaveOptions = Field(default_factory=AssetSaveOptions)
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
    usage: TokenUsage | None = None


class ProviderTextGenerationResult(BaseModel):
    provider_request_id: str | None = None
    output_text: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    usage: TokenUsage | None = None


class MediaGenerationResponse(BaseModel):
    generation_id: str
    capability: ModelCapability
    provider_id: str
    model: str
    resolved_prompt: str
    provider_request_id: str | None = None
    outputs: list[GeneratedMediaOutput]
    usage: TokenUsage | None = None
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


class MultiVideoSegmentGenerationResult(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    segment_index: int = Field(ge=1)
    title: str
    duration_seconds: int = Field(ge=1)
    visual_prompt: str
    narration_text: str
    use_previous_segment_last_frame: bool = False
    resolved_prompt: str
    status: Literal["success", "error"]
    generation: MediaGenerationResponse | None = None
    token_usage: TokenUsage | None = None
    error_detail: str | None = None


class MultiVideoGenerationResponse(BaseModel):
    batch_id: str
    provider_id: str
    model: str
    prompt: str
    segment_count: int
    segments: list[MultiVideoSegmentGenerationResult] = Field(default_factory=list)


class VideoGenerationTaskResponse(BaseModel):
    task_id: str
    task_kind: Literal["single", "multi"]
    status: Literal["queued", "running", "completed", "failed"]
    provider_id: str
    model: str
    request_summary: str
    prompt: str | None = None
    scene_prompt_texts: list[str] = Field(default_factory=list)
    requested_count: int = Field(default=1, ge=1)
    requested_segment_count: int | None = Field(default=None, ge=1)
    error_detail: str | None = None
    result: MediaGenerationResponse | None = None
    batch_result: MultiVideoGenerationResponse | None = None
    created_at: datetime
    updated_at: datetime


class VideoGenerationTaskListResponse(BaseModel):
    items: list[VideoGenerationTaskResponse] = Field(default_factory=list)
