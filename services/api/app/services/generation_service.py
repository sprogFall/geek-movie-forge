from __future__ import annotations

import json
import logging
import math
import re
import time
from uuid import uuid4

from packages.provider_sdk.gateway import ProviderGateway
from packages.shared.contracts.assets import AssetCreateRequest, AssetResponse
from packages.shared.contracts.call_logs import CallLogStatus, TokenUsage as CallLogTokenUsage
from packages.shared.contracts.generations import (
    ImageGenerationPayload,
    ImageGenerationRequest,
    MediaGenerationResponse,
    MultiVideoGenerationRequest,
    MultiVideoGenerationResponse,
    MultiVideoPlanRequest,
    MultiVideoPlanResponse,
    MultiVideoSegmentGenerationResult,
    MultiVideoSegmentRegenerationRequest,
    ProviderMediaGenerationResult,
    ProviderTextGenerationResult,
    TextGenerationPayload,
    TextGenerationRequest,
    TextGenerationResponse,
    TokenUsage as GenerationTokenUsage,
    VideoInputMaterial,
    VideoGenerationPayload,
    VideoGenerationRequest,
    VideoSegmentPlan,
)
from packages.shared.contracts.providers import ProviderRecord
from packages.shared.enums.asset_origin import AssetOrigin
from packages.shared.enums.asset_type import AssetType
from packages.shared.enums.model_capability import ModelCapability
from services.api.app.services.asset_service import InMemoryAssetService
from services.api.app.services.call_log_service import InMemoryCallLogService
from services.api.app.services.errors import ServiceError, UpstreamServiceError, ValidationServiceError
from services.api.app.services.provider_service import InMemoryProviderService


class GenerationService:
    def __init__(
        self,
        *,
        provider_service: InMemoryProviderService,
        asset_service: InMemoryAssetService,
        provider_gateway: ProviderGateway,
        call_log_service: InMemoryCallLogService | None = None,
    ) -> None:
        self._provider_service = provider_service
        self._asset_service = asset_service
        self._provider_gateway = provider_gateway
        self._call_log_service = call_log_service

    async def generate_image(
        self,
        owner_id: str,
        payload: ImageGenerationRequest,
    ) -> MediaGenerationResponse:
        provider, _ = self._provider_service.ensure_model_capability(
            owner_id,
            payload.provider_id,
            payload.model,
            ModelCapability.IMAGE,
        )
        gateway_payload = ImageGenerationPayload(
            provider_id=payload.provider_id,
            model=payload.model,
            count=payload.count,
            prompt=payload.prompt,
            preset_prompt=payload.preset_prompt,
            resolved_prompt=_merge_prompt(payload.preset_prompt, payload.prompt),
            options=payload.options,
        )
        provider_result = await self._log_and_call(
            owner_id=owner_id,
            provider=provider,
            model=payload.model,
            capability=ModelCapability.IMAGE,
            request_summary=gateway_payload.resolved_prompt or "",
            coro=self._provider_gateway.generate_image(provider, gateway_payload),
        )
        saved_assets = self._save_media_assets(
            owner_id=owner_id,
            capability=ModelCapability.IMAGE,
            provider_id=provider.provider_id,
            model=payload.model,
            outputs=provider_result.outputs,
            category=payload.save.category,
            name_prefix=payload.save.name_prefix,
            tags=payload.save.tags,
            enabled=payload.save.enabled,
        )
        return MediaGenerationResponse(
            generation_id=f"gen_{uuid4().hex[:12]}",
            capability=ModelCapability.IMAGE,
            provider_id=payload.provider_id,
            model=payload.model,
            resolved_prompt=gateway_payload.resolved_prompt,
            provider_request_id=provider_result.provider_request_id,
            outputs=provider_result.outputs,
            saved_assets=saved_assets,
        )

    async def generate_video(
        self,
        owner_id: str,
        payload: VideoGenerationRequest,
    ) -> MediaGenerationResponse:
        provider, _ = self._provider_service.ensure_model_capability(
            owner_id,
            payload.provider_id,
            payload.model,
            ModelCapability.VIDEO,
        )
        image_materials = self._resolve_image_materials(
            owner_id,
            payload.image_material_asset_ids,
        )
        image_materials.extend(
            VideoInputMaterial(kind="url", value=value)
            for value in payload.image_material_urls
        )
        scene_prompt_texts = self._resolve_scene_prompt_materials(
            owner_id,
            payload.scene_prompt_asset_ids,
        )
        scene_prompt_texts.extend(payload.scene_prompt_texts)
        return await self._generate_video_with_resolved_inputs(
            owner_id=owner_id,
            provider=provider,
            model=payload.model,
            count=payload.count,
            prompt=payload.prompt,
            preset_prompt=payload.preset_prompt,
            image_materials=image_materials,
            scene_prompt_texts=scene_prompt_texts,
            save=payload.save,
            options=payload.options,
        )

    async def generate_text(
        self,
        owner_id: str,
        payload: TextGenerationRequest,
    ) -> TextGenerationResponse:
        logger = logging.getLogger(__name__)
        logger.info(
            "generate_text request: %s",
            {
                "owner_id": owner_id,
                "provider_id": payload.provider_id,
                "model": payload.model,
                "task_type": payload.task_type,
                "source_text_len": len(payload.source_text),
                "source_text_preview": _preview_text(payload.source_text),
                "prompt_preview": _preview_text(payload.prompt),
                "preset_prompt_preview": _preview_text(payload.preset_prompt),
                "options_keys": sorted(payload.options.keys()),
                "save_enabled": payload.save.enabled,
                "save_category": payload.save.category,
            },
        )
        provider, _ = self._provider_service.ensure_model_capability(
            owner_id,
            payload.provider_id,
            payload.model,
            ModelCapability.TEXT,
        )
        user_resolved_prompt = _merge_prompt(payload.preset_prompt, payload.prompt) or None
        provider_resolved_prompt = _build_text_generation_prompt(
            payload.task_type,
            user_resolved_prompt,
        )
        gateway_payload = TextGenerationPayload(
            provider_id=payload.provider_id,
            model=payload.model,
            task_type=payload.task_type,
            source_text=payload.source_text,
            prompt=payload.prompt,
            preset_prompt=payload.preset_prompt,
            resolved_prompt=provider_resolved_prompt,
            options=_enrich_text_generation_options(payload.options),
        )
        provider_result = await self._log_and_call(
            owner_id=owner_id,
            provider=provider,
            model=payload.model,
            capability=ModelCapability.TEXT,
            request_summary=provider_resolved_prompt or payload.source_text or "",
            coro=self._provider_gateway.generate_text(provider, gateway_payload),
        )
        output_text = _sanitize_text_output(
            provider_result.output_text,
            task_type=payload.task_type,
        )
        saved_assets: list[AssetResponse] = []
        if payload.save.enabled:
            saved_assets.append(
                self._asset_service.create_asset(
                    owner_id,
                    AssetCreateRequest(
                        asset_type=AssetType.TEXT,
                        category=payload.save.category or AssetType.TEXT.value,
                        name=(payload.save.name_prefix or "text-result"),
                        content_text=output_text,
                        tags=payload.save.tags,
                        provider_id=provider.provider_id,
                        model=payload.model,
                    ),
                    origin=AssetOrigin.GENERATED,
                )
            )
        response = TextGenerationResponse(
            generation_id=f"gen_{uuid4().hex[:12]}",
            capability=ModelCapability.TEXT,
            provider_id=payload.provider_id,
            model=payload.model,
            task_type=payload.task_type,
            source_text=payload.source_text,
            resolved_prompt=user_resolved_prompt,
            provider_request_id=provider_result.provider_request_id,
            output_text=output_text,
            saved_assets=saved_assets,
        )
        logger.info(
            "generate_text response: %s",
            {
                "owner_id": owner_id,
                "generation_id": response.generation_id,
                "provider_id": response.provider_id,
                "model": response.model,
                "provider_request_id": response.provider_request_id,
                "output_text_len": len(response.output_text),
                "output_text_preview": _preview_text(response.output_text, limit=200),
                "saved_assets_count": len(response.saved_assets),
            },
        )
        return response

    async def plan_multi_video(
        self,
        owner_id: str,
        payload: MultiVideoPlanRequest,
    ) -> MultiVideoPlanResponse:
        provider, _ = self._provider_service.ensure_model_capability(
            owner_id,
            payload.provider_id,
            payload.model,
            ModelCapability.TEXT,
        )
        scene_prompt_texts = self._resolve_scene_prompt_materials(
            owner_id,
            payload.scene_prompt_asset_ids,
        )
        scene_prompt_texts.extend(payload.scene_prompt_texts)
        segment_durations = _plan_segment_durations(
            payload.total_duration_seconds,
            payload.segment_duration_seconds,
        )
        source_text = _build_multi_video_plan_source_text(
            prompt=payload.prompt,
            total_duration_seconds=payload.total_duration_seconds,
            segment_durations=segment_durations,
            scene_prompt_texts=scene_prompt_texts,
        )
        resolved_prompt = _build_multi_video_planning_prompt(len(segment_durations))
        gateway_payload = TextGenerationPayload(
            provider_id=payload.provider_id,
            model=payload.model,
            task_type="video_segmentation_plan",
            source_text=source_text,
            prompt=payload.prompt,
            preset_prompt=payload.preset_prompt,
            resolved_prompt=resolved_prompt,
            options=_enrich_text_generation_options(payload.options),
        )
        provider_result = await self._log_and_call(
            owner_id=owner_id,
            provider=provider,
            model=payload.model,
            capability=ModelCapability.TEXT,
            request_summary=payload.prompt or source_text,
            coro=self._provider_gateway.generate_text(provider, gateway_payload),
        )
        segments = _parse_multi_video_segments(
            provider_result.output_text,
            segment_durations,
        )
        return MultiVideoPlanResponse(
            plan_id=f"plan_{uuid4().hex[:12]}",
            provider_id=payload.provider_id,
            model=payload.model,
            prompt=payload.prompt or "",
            resolved_prompt=resolved_prompt,
            total_duration_seconds=payload.total_duration_seconds,
            segment_duration_seconds=payload.segment_duration_seconds,
            segment_count=len(segments),
            provider_request_id=provider_result.provider_request_id,
            usage=provider_result.usage,
            segments=segments,
        )

    async def generate_multi_video(
        self,
        owner_id: str,
        payload: MultiVideoGenerationRequest,
    ) -> MultiVideoGenerationResponse:
        provider, _ = self._provider_service.ensure_model_capability(
            owner_id,
            payload.provider_id,
            payload.model,
            ModelCapability.VIDEO,
        )
        global_scene_prompt_texts = self._resolve_scene_prompt_materials(
            owner_id,
            payload.scene_prompt_asset_ids,
        )
        global_scene_prompt_texts.extend(payload.scene_prompt_texts)
        base_image_materials = self._resolve_image_materials(
            owner_id,
            payload.image_material_asset_ids,
        )
        base_image_materials.extend(
            VideoInputMaterial(kind="url", value=value)
            for value in payload.image_material_urls
        )
        segments: list[MultiVideoSegmentGenerationResult] = []
        previous_segment_last_frame: VideoInputMaterial | None = None
        for segment in payload.segments:
            segment_image_materials = _build_multi_video_segment_image_materials(
                base_materials=base_image_materials,
                previous_segment_last_frame=previous_segment_last_frame,
                segment=segment,
                provider_adapter_type=provider.adapter_type,
            )
            segment_result = await self._generate_multi_video_segment(
                owner_id=owner_id,
                provider=provider,
                model=payload.model,
                prompt=payload.prompt,
                preset_prompt=payload.preset_prompt,
                segment=segment,
                image_materials=segment_image_materials,
                scene_prompt_texts=global_scene_prompt_texts,
                provider_adapter_type=provider.adapter_type,
                save=payload.save,
                options=payload.options,
            )
            segments.append(segment_result)
            previous_segment_last_frame = _extract_last_frame_material(segment_result)
        return MultiVideoGenerationResponse(
            batch_id=f"batch_{uuid4().hex[:12]}",
            provider_id=payload.provider_id,
            model=payload.model,
            prompt=payload.prompt or "",
            segment_count=len(segments),
            segments=segments,
        )

    async def regenerate_multi_video_segment(
        self,
        owner_id: str,
        payload: MultiVideoSegmentRegenerationRequest,
    ) -> MultiVideoSegmentGenerationResult:
        provider, _ = self._provider_service.ensure_model_capability(
            owner_id,
            payload.provider_id,
            payload.model,
            ModelCapability.VIDEO,
        )
        scene_prompt_texts = self._resolve_scene_prompt_materials(
            owner_id,
            payload.scene_prompt_asset_ids,
        )
        scene_prompt_texts.extend(payload.scene_prompt_texts)
        image_materials = self._resolve_image_materials(
            owner_id,
            payload.image_material_asset_ids,
        )
        image_materials.extend(
            VideoInputMaterial(kind="url", value=value)
            for value in payload.image_material_urls
        )
        previous_segment_last_frame = _resolve_previous_segment_last_frame(
            url=payload.previous_segment_last_frame_url,
            base64_data=payload.previous_segment_last_frame_base64,
        )
        segment_image_materials = _build_multi_video_segment_image_materials(
            base_materials=image_materials,
            previous_segment_last_frame=previous_segment_last_frame,
            segment=payload.segment,
            provider_adapter_type=provider.adapter_type,
        )
        return await self._generate_multi_video_segment(
            owner_id=owner_id,
            provider=provider,
            model=payload.model,
            prompt=payload.prompt,
            preset_prompt=payload.preset_prompt,
            segment=payload.segment,
            image_materials=segment_image_materials,
            scene_prompt_texts=scene_prompt_texts,
            provider_adapter_type=provider.adapter_type,
            save=payload.save,
            options=payload.options,
        )

    async def _log_and_call(
        self,
        *,
        owner_id: str,
        provider: ProviderRecord,
        model: str,
        capability: ModelCapability,
        request_summary: str,
        coro,
    ):
        logger = logging.getLogger(__name__)
        start = time.monotonic()
        try:
            logger.info(
                "provider_call start: %s",
                {
                    "owner_id": owner_id,
                    "provider_id": provider.provider_id,
                    "provider_name": provider.name,
                    "model": model,
                    "capability": capability.value,
                    "request_preview": _preview_text(request_summary, limit=200),
                },
            )
            result = await coro
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.info(
                "provider_call success: %s",
                {
                    "owner_id": owner_id,
                    "provider_id": provider.provider_id,
                    "model": model,
                    "capability": capability.value,
                    "duration_ms": duration_ms,
                },
            )
            if self._call_log_service:
                try:
                    self._call_log_service.log_call(
                        owner_id=owner_id,
                        provider_id=provider.provider_id,
                        provider_name=provider.name,
                        model=model,
                        capability=capability.value,
                        request_body_summary=request_summary[:200],
                        response_status=CallLogStatus.SUCCESS,
                        duration_ms=duration_ms,
                        token_usage=_to_call_log_token_usage(_extract_usage(result)),
                    )
                except Exception:
                    logger.warning("Failed to write success call log", exc_info=True)
            return result
        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.warning(
                "provider_call error: %s",
                {
                    "owner_id": owner_id,
                    "provider_id": provider.provider_id,
                    "model": model,
                    "capability": capability.value,
                    "duration_ms": duration_ms,
                    "error": str(exc)[:500],
                },
                exc_info=True,
            )
            if self._call_log_service:
                try:
                    self._call_log_service.log_call(
                        owner_id=owner_id,
                        provider_id=provider.provider_id,
                        provider_name=provider.name,
                        model=model,
                        capability=capability.value,
                        request_body_summary=request_summary[:200],
                        response_status=CallLogStatus.ERROR,
                        error_detail=str(exc)[:1000],
                        duration_ms=duration_ms,
                    )
                except Exception:
                    logger.warning("Failed to write error call log", exc_info=True)
            # Re-raise ServiceError (e.g. UpstreamServiceError from gateway) as-is
            if isinstance(exc, ServiceError):
                raise
            raise UpstreamServiceError(f"Provider call failed: {exc}") from exc

    async def _generate_video_with_resolved_inputs(
        self,
        *,
        owner_id: str,
        provider: ProviderRecord,
        model: str,
        count: int,
        prompt: str | None,
        preset_prompt: str | None,
        image_materials: list[VideoInputMaterial],
        scene_prompt_texts: list[str],
        save,
        options: dict,
    ) -> MediaGenerationResponse:
        image_urls = [item.value for item in image_materials if item.kind == "url"]
        image_base64 = [item.value for item in image_materials if item.kind == "base64"]
        base_prompt = _merge_prompt(preset_prompt, prompt) or None
        resolved_prompt = _build_video_resolved_prompt(base_prompt, scene_prompt_texts)

        gateway_payload = VideoGenerationPayload(
            provider_id=provider.provider_id,
            model=model,
            count=count,
            prompt=prompt,
            preset_prompt=preset_prompt,
            resolved_prompt=resolved_prompt,
            image_materials=image_materials,
            image_material_urls=image_urls,
            image_material_base64=image_base64,
            scene_prompt_texts=scene_prompt_texts,
            options=_build_video_generation_options(
                options,
                provider_adapter_type=provider.adapter_type,
            ),
        )
        provider_result = await self._log_and_call(
            owner_id=owner_id,
            provider=provider,
            model=model,
            capability=ModelCapability.VIDEO,
            request_summary=gateway_payload.resolved_prompt or "",
            coro=self._provider_gateway.generate_video(provider, gateway_payload),
        )
        saved_assets = self._save_media_assets(
            owner_id=owner_id,
            capability=ModelCapability.VIDEO,
            provider_id=provider.provider_id,
            model=model,
            outputs=provider_result.outputs,
            category=save.category,
            name_prefix=save.name_prefix,
            tags=save.tags,
            enabled=save.enabled,
        )
        return MediaGenerationResponse(
            generation_id=f"gen_{uuid4().hex[:12]}",
            capability=ModelCapability.VIDEO,
            provider_id=provider.provider_id,
            model=model,
            resolved_prompt=resolved_prompt or "",
            provider_request_id=provider_result.provider_request_id,
            outputs=provider_result.outputs,
            usage=_extract_usage(provider_result),
            saved_assets=saved_assets,
        )

    async def _generate_multi_video_segment(
        self,
        *,
        owner_id: str,
        provider: ProviderRecord,
        model: str,
        prompt: str | None,
        preset_prompt: str | None,
        segment: VideoSegmentPlan,
        image_materials: list[VideoInputMaterial],
        scene_prompt_texts: list[str],
        provider_adapter_type: str,
        save,
        options: dict,
    ) -> MultiVideoSegmentGenerationResult:
        segment_prompt = _build_multi_video_segment_prompt(
            prompt=prompt,
            preset_prompt=preset_prompt,
            segment=segment,
        )
        segment_options = _build_multi_video_segment_options(
            options,
            segment,
            provider_adapter_type=provider_adapter_type,
            image_material_count=len(image_materials),
        )
        if save.enabled:
            name_prefix = save.name_prefix or "multi-video"
            segment_save = save.model_copy(
                update={"name_prefix": f"{name_prefix}-seg-{segment.segment_index}"}
            )
        else:
            segment_save = save

        try:
            generation = await self._generate_video_with_resolved_inputs(
                owner_id=owner_id,
                provider=provider,
                model=model,
                count=1,
                prompt=segment_prompt,
                preset_prompt=None,
                image_materials=image_materials,
                scene_prompt_texts=scene_prompt_texts,
                save=segment_save,
                options=segment_options,
            )
            return MultiVideoSegmentGenerationResult(
                segment_index=segment.segment_index,
                title=segment.title,
                duration_seconds=segment.duration_seconds,
                visual_prompt=segment.visual_prompt,
                narration_text=segment.narration_text,
                use_previous_segment_last_frame=segment.use_previous_segment_last_frame,
                resolved_prompt=generation.resolved_prompt,
                status="success",
                generation=generation,
                token_usage=generation.usage,
            )
        except ServiceError as exc:
            return MultiVideoSegmentGenerationResult(
                segment_index=segment.segment_index,
                title=segment.title,
                duration_seconds=segment.duration_seconds,
                visual_prompt=segment.visual_prompt,
                narration_text=segment.narration_text,
                use_previous_segment_last_frame=segment.use_previous_segment_last_frame,
                resolved_prompt=segment_prompt,
                status="error",
                error_detail=exc.detail,
            )

    def _resolve_image_materials(
        self,
        owner_id: str,
        asset_ids: list[str],
    ) -> list[VideoInputMaterial]:
        materials: list[VideoInputMaterial] = []
        for asset_id in asset_ids:
            asset = self._asset_service.require_asset(owner_id, asset_id)
            if asset.asset_type != AssetType.IMAGE:
                raise ValidationServiceError("Image material asset must be image type")
            if asset.content_url is not None:
                materials.append(VideoInputMaterial(kind="url", value=str(asset.content_url)))
                continue
            if asset.content_base64 is not None:
                materials.append(
                    VideoInputMaterial(
                        kind="base64",
                        value=_normalize_image_data_uri(
                            asset.content_base64,
                            asset.mime_type,
                        ),
                    )
                )
                continue
            raise ValidationServiceError("Image material asset has no usable content")
        return materials

    def _resolve_scene_prompt_materials(
        self,
        owner_id: str,
        asset_ids: list[str],
    ) -> list[str]:
        prompts: list[str] = []
        for asset_id in asset_ids:
            asset = self._asset_service.require_asset(owner_id, asset_id)
            if asset.asset_type != AssetType.TEXT:
                raise ValidationServiceError("Scene prompt asset must be text type")
            if not asset.content_text:
                raise ValidationServiceError("Scene prompt asset has no text content")
            prompts.append(asset.content_text)
        return prompts

    def _save_media_assets(
        self,
        *,
        owner_id: str,
        capability: ModelCapability,
        provider_id: str,
        model: str,
        outputs,
        category: str | None,
        name_prefix: str | None,
        tags: list[str],
        enabled: bool,
    ) -> list[AssetResponse]:
        if not enabled:
            return []

        asset_type = _asset_type_for_capability(capability)
        saved_assets: list[AssetResponse] = []
        for index, output in enumerate(outputs, start=1):
            if output.url is None and output.base64_data is None:
                raise ValidationServiceError("Generated output has no storable media content")
            saved_assets.append(
                self._asset_service.create_asset(
                    owner_id,
                    AssetCreateRequest(
                        asset_type=asset_type,
                        category=category or asset_type.value,
                        name=_asset_name(name_prefix, capability, index),
                        content_url=output.url,
                        content_base64=output.base64_data,
                        mime_type=output.mime_type,
                        tags=tags,
                        metadata=output.metadata,
                        provider_id=provider_id,
                        model=model,
                    ),
                    origin=AssetOrigin.GENERATED,
                )
            )
        return saved_assets


def _build_text_generation_prompt(
    task_type: str,
    user_prompt: str | None,
) -> str:
    instructions = [
        "你是专业中文影视文案助手。",
        "只输出简体中文结果。",
        "禁止输出 Python、代码、JSON、Markdown 代码块、英文说明、前言、后记或规则解释。",
        "直接输出最终可用正文，不要写“下面是结果”“当然可以”等套话。",
    ]
    if task_type.strip().lower() in {"script", "script_writing", "caption", "copy"}:
        instructions.append("输出内容必须贴近视频画面与叙事，优先写成可直接用于视频创作的中文脚本或文案。")
    if user_prompt:
        instructions.append("用户附加要求：")
        instructions.append(user_prompt)
    return "\n".join(instructions)


def _enrich_text_generation_options(options: dict) -> dict:
    enriched = dict(options)
    enriched.setdefault("output_language", "zh-CN")
    enriched.setdefault("response_format_hint", "plain_text")
    return enriched


def _sanitize_text_output(text: str, *, task_type: str) -> str:
    normalized = _strip_code_fences(text).strip()
    if not normalized:
        raise UpstreamServiceError("文本模型返回空内容")
    if _looks_like_source_code(normalized):
        raise UpstreamServiceError("文本模型返回了代码内容，请重试或调整提示词")
    if _should_enforce_chinese(task_type) and not _contains_chinese(normalized):
        raise UpstreamServiceError("文本模型返回了非中文内容，请重试或调整提示词")
    return normalized


def _strip_code_fences(text: str) -> str:
    value = (text or "").strip()
    if value.startswith("```") and value.endswith("```"):
        value = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", value)
        value = re.sub(r"\s*```$", "", value)
    return value.strip()


def _looks_like_source_code(text: str) -> bool:
    code_markers = (
        "```",
        "import ",
        "from ",
        "def ",
        "class ",
        "print(",
        "return ",
        "if __name__ ==",
        "console.log(",
    )
    stripped = text.strip()
    first_line = stripped.splitlines()[0] if stripped else ""
    return any(marker in stripped for marker in code_markers) or first_line.endswith(":")


def _should_enforce_chinese(task_type: str) -> bool:
    return task_type.strip().lower() not in {"translate_en", "translate_english"}


def _contains_chinese(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def _build_video_resolved_prompt(
    base_prompt: str | None,
    scene_prompt_texts: list[str],
) -> str | None:
    parts = [part for part in [base_prompt] if part]
    if scene_prompt_texts:
        parts.append("请严格贴合以下中文剧情/分镜线索生成视频：")
        parts.extend(
            f"{index}. {item}"
            for index, item in enumerate(scene_prompt_texts, start=1)
            if item.strip()
        )
    if not parts:
        return None
    return "\n".join(parts)


def _plan_segment_durations(total_duration_seconds: int, segment_duration_seconds: int) -> list[int]:
    segment_count = max(1, math.ceil(total_duration_seconds / segment_duration_seconds))
    durations = [segment_duration_seconds] * segment_count
    remainder = total_duration_seconds - segment_duration_seconds * (segment_count - 1)
    durations[-1] = remainder
    return durations


def _build_multi_video_plan_source_text(
    *,
    prompt: str | None,
    total_duration_seconds: int,
    segment_durations: list[int],
    scene_prompt_texts: list[str],
) -> str:
    lines = [
        f"总视频时长：{total_duration_seconds} 秒",
        f"分段数量：{len(segment_durations)}",
        f"每段时长：{', '.join(f'{item}秒' for item in segment_durations)}",
    ]
    if prompt:
        lines.extend(["核心创作需求：", prompt])
    if scene_prompt_texts:
        lines.append("补充文本素材：")
        lines.extend(
            f"{index}. {item}" for index, item in enumerate(scene_prompt_texts, start=1)
        )
    return "\n".join(lines)


def _build_multi_video_planning_prompt(segment_count: int) -> str:
    return "\n".join(
        [
            "你是短视频分镜策划助手，只能输出 JSON 对象。",
            "禁止输出 Markdown、解释、代码块或额外文字。",
            f"请严格输出 {segment_count} 个分段。",
            'JSON 格式：{"segments":[{"title":"", "visual_prompt":"", "narration_text":""}]}',
            "每段都必须使用简体中文，内容要和用户提示强关联，镜头描述具体，可直接用于视频生成。",
        ]
    )


def _parse_multi_video_segments(
    output_text: str,
    segment_durations: list[int],
) -> list[VideoSegmentPlan]:
    parsed = _extract_json_object(output_text)
    raw_segments = parsed.get("segments")
    if not isinstance(raw_segments, list):
        raise UpstreamServiceError("分镜规划结果缺少 segments 数组")
    if len(raw_segments) != len(segment_durations):
        raise UpstreamServiceError("分镜规划返回的分段数量与目标数量不一致")

    segments: list[VideoSegmentPlan] = []
    for index, (raw_item, duration_seconds) in enumerate(
        zip(raw_segments, segment_durations, strict=True),
        start=1,
    ):
        if not isinstance(raw_item, dict):
            raise UpstreamServiceError("分镜规划的 segment 数据格式无效")
        title = _coerce_plan_text(raw_item.get("title")) or f"第 {index} 段"
        visual_prompt = _coerce_plan_text(
            raw_item.get("visual_prompt") or raw_item.get("prompt") or raw_item.get("shot_description")
        )
        narration_text = _coerce_plan_text(
            raw_item.get("narration_text") or raw_item.get("script") or raw_item.get("voiceover")
        )
        if not visual_prompt or not narration_text:
            raise UpstreamServiceError("分镜规划缺少 visual_prompt 或 narration_text")
        segments.append(
            VideoSegmentPlan(
                segment_index=index,
                title=title,
                duration_seconds=duration_seconds,
                visual_prompt=visual_prompt,
                narration_text=narration_text,
            )
        )
    return segments


def _extract_json_object(text: str) -> dict:
    cleaned = _strip_code_fences(text)
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise UpstreamServiceError("分镜规划结果不是有效 JSON")
    try:
        parsed = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise UpstreamServiceError("分镜规划结果解析失败") from exc
    if not isinstance(parsed, dict):
        raise UpstreamServiceError("分镜规划结果不是有效 JSON 对象")
    return parsed


def _coerce_plan_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _build_multi_video_segment_prompt(
    *,
    prompt: str | None,
    preset_prompt: str | None,
    segment: VideoSegmentPlan,
) -> str:
    parts = [part for part in (_merge_prompt(preset_prompt, prompt),) if part]
    parts.extend(
        [
            f"当前仅生成第 {segment.segment_index} 段视频。",
            "只允许使用当前分段信息，禁止引用、延续或复用其他分段的画面、台词、旁白或上下文。",
            f"段落标题：{segment.title}",
            f"目标时长：{segment.duration_seconds} 秒",
            f"画面提示：{segment.visual_prompt}",
            f"文案脚本（仅本段）：{segment.narration_text}",
        ]
    )
    parts.append("如果模型支持自动生成音频或旁白，只能围绕本段文案，不要说出其他分段内容。")
    parts.append("请确保视频画面与上述文案和镜头提示强关联。")
    return "\n".join(parts)


def _build_multi_video_segment_options(
    options: dict,
    segment: VideoSegmentPlan,
    *,
    provider_adapter_type: str,
    image_material_count: int,
) -> dict:
    segment_options = _build_video_generation_options(
        options,
        provider_adapter_type=provider_adapter_type,
    )
    segment_options.setdefault("duration", segment.duration_seconds)
    segment_options.setdefault("duration_seconds", segment.duration_seconds)
    if (
        provider_adapter_type == "volcengine_ark"
        and segment.use_previous_segment_last_frame
        and "input_mode" not in segment_options
    ):
        if image_material_count <= 1:
            segment_options["input_mode"] = "first_frame"
        else:
            segment_options["input_mode"] = "first_last_frame"
    return segment_options


def _build_video_generation_options(
    options: dict,
    *,
    provider_adapter_type: str,
) -> dict:
    enriched = dict(options)
    if provider_adapter_type == "volcengine_ark":
        enriched["generate_audio"] = True
    return enriched


def _build_multi_video_segment_image_materials(
    *,
    base_materials: list[VideoInputMaterial],
    previous_segment_last_frame: VideoInputMaterial | None,
    segment: VideoSegmentPlan,
    provider_adapter_type: str,
) -> list[VideoInputMaterial]:
    materials = list(base_materials)
    if not segment.use_previous_segment_last_frame or previous_segment_last_frame is None:
        return materials

    stitched_materials = [previous_segment_last_frame, *materials]
    if provider_adapter_type != "volcengine_ark":
        return stitched_materials

    # Volcengine first/last-frame mode only accepts up to 2 images.
    return stitched_materials[:2]


def _extract_last_frame_material(
    segment: MultiVideoSegmentGenerationResult,
) -> VideoInputMaterial | None:
    if segment.status != "success" or segment.generation is None:
        return None
    for output in segment.generation.outputs:
        metadata = output.metadata or {}
        last_frame_url = _coerce_plan_text(
            metadata.get("last_frame_url")
            or metadata.get("end_frame_url")
            or metadata.get("tail_frame_url")
        )
        if last_frame_url:
            return VideoInputMaterial(kind="url", value=last_frame_url)
        last_frame_base64 = _coerce_plan_text(
            metadata.get("last_frame_base64")
            or metadata.get("end_frame_base64")
            or metadata.get("tail_frame_base64")
        )
        if last_frame_base64:
            return VideoInputMaterial(
                kind="base64",
                value=_normalize_image_data_uri(last_frame_base64, "image/png"),
            )
        if output.cover_image_url:
            return VideoInputMaterial(kind="url", value=output.cover_image_url)
    return None


def _resolve_previous_segment_last_frame(
    *,
    url: str | None,
    base64_data: str | None,
) -> VideoInputMaterial | None:
    normalized_url = _coerce_plan_text(url)
    if normalized_url:
        return VideoInputMaterial(kind="url", value=normalized_url)

    normalized_base64 = _coerce_plan_text(base64_data)
    if normalized_base64:
        return VideoInputMaterial(
            kind="base64",
            value=_normalize_image_data_uri(normalized_base64, "image/png"),
        )

    return None


def _extract_usage(result: object) -> GenerationTokenUsage | None:
    usage = getattr(result, "usage", None)
    if isinstance(usage, GenerationTokenUsage):
        return usage
    return None


def _to_call_log_token_usage(usage: GenerationTokenUsage | None) -> CallLogTokenUsage | None:
    if usage is None:
        return None
    return CallLogTokenUsage(
        prompt_tokens=usage.input_tokens,
        completion_tokens=usage.output_tokens,
        total_tokens=usage.total_tokens,
    )


def _merge_prompt(preset_prompt: str | None, prompt: str | None) -> str:
    parts = [part for part in (preset_prompt, prompt) if part]
    return "\n".join(parts)


def _asset_type_for_capability(capability: ModelCapability) -> AssetType:
    mapping = {
        ModelCapability.IMAGE: AssetType.IMAGE,
        ModelCapability.VIDEO: AssetType.VIDEO,
        ModelCapability.TEXT: AssetType.TEXT,
    }
    return mapping[capability]


def _asset_name(name_prefix: str | None, capability: ModelCapability, index: int) -> str:
    prefix = name_prefix or f"{capability.value}-result"
    return f"{prefix}-{index}"


def _preview_text(text: str | None, *, limit: int = 200) -> str | None:
    if text is None:
        return None
    value = text.strip()
    if not value:
        return None
    value = value.replace("\n", "\\n")
    if len(value) <= limit:
        return value
    return f"{value[:limit]}..."


def _normalize_image_data_uri(value: str, mime_type: str | None) -> str:
    normalized = value.strip()
    if normalized.startswith("data:"):
        return normalized
    return f"data:{mime_type or 'image/png'};base64,{normalized}"
