from __future__ import annotations

import logging
import time
from uuid import uuid4

from packages.provider_sdk.gateway import ProviderGateway
from packages.shared.contracts.assets import AssetCreateRequest, AssetResponse
from packages.shared.contracts.call_logs import CallLogStatus
from packages.shared.contracts.generations import (
    ImageGenerationPayload,
    ImageGenerationRequest,
    MediaGenerationResponse,
    TextGenerationPayload,
    TextGenerationRequest,
    TextGenerationResponse,
    VideoGenerationPayload,
    VideoGenerationRequest,
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
        image_urls, image_base64 = self._resolve_image_materials(
            owner_id,
            payload.image_material_asset_ids,
        )
        image_urls.extend(payload.image_material_urls)
        scene_prompt_texts = self._resolve_scene_prompt_materials(
            owner_id,
            payload.scene_prompt_asset_ids,
        )
        scene_prompt_texts.extend(payload.scene_prompt_texts)

        gateway_payload = VideoGenerationPayload(
            provider_id=payload.provider_id,
            model=payload.model,
            count=payload.count,
            prompt=payload.prompt,
            preset_prompt=payload.preset_prompt,
            resolved_prompt=_merge_prompt(payload.preset_prompt, payload.prompt),
            image_material_urls=image_urls,
            image_material_base64=image_base64,
            scene_prompt_texts=scene_prompt_texts,
            options=payload.options,
        )
        provider_result = await self._log_and_call(
            owner_id=owner_id,
            provider=provider,
            model=payload.model,
            capability=ModelCapability.VIDEO,
            request_summary=gateway_payload.resolved_prompt or "",
            coro=self._provider_gateway.generate_video(provider, gateway_payload),
        )
        saved_assets = self._save_media_assets(
            owner_id=owner_id,
            capability=ModelCapability.VIDEO,
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
            capability=ModelCapability.VIDEO,
            provider_id=payload.provider_id,
            model=payload.model,
            resolved_prompt=gateway_payload.resolved_prompt,
            provider_request_id=provider_result.provider_request_id,
            outputs=provider_result.outputs,
            saved_assets=saved_assets,
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
        resolved_prompt = _merge_prompt(payload.preset_prompt, payload.prompt) or None
        gateway_payload = TextGenerationPayload(
            provider_id=payload.provider_id,
            model=payload.model,
            task_type=payload.task_type,
            source_text=payload.source_text,
            prompt=payload.prompt,
            preset_prompt=payload.preset_prompt,
            resolved_prompt=resolved_prompt,
            options=payload.options,
        )
        provider_result = await self._log_and_call(
            owner_id=owner_id,
            provider=provider,
            model=payload.model,
            capability=ModelCapability.TEXT,
            request_summary=resolved_prompt or payload.source_text or "",
            coro=self._provider_gateway.generate_text(provider, gateway_payload),
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
                        content_text=provider_result.output_text,
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
            resolved_prompt=resolved_prompt,
            provider_request_id=provider_result.provider_request_id,
            output_text=provider_result.output_text,
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

    def _resolve_image_materials(
        self,
        owner_id: str,
        asset_ids: list[str],
    ) -> tuple[list[str], list[str]]:
        image_urls: list[str] = []
        image_base64: list[str] = []
        for asset_id in asset_ids:
            asset = self._asset_service.require_asset(owner_id, asset_id)
            if asset.asset_type != AssetType.IMAGE:
                raise ValidationServiceError("Image material asset must be image type")
            if asset.content_url is not None:
                image_urls.append(str(asset.content_url))
                continue
            if asset.content_base64 is not None:
                image_base64.append(asset.content_base64)
                continue
            raise ValidationServiceError("Image material asset has no usable content")
        return image_urls, image_base64

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
