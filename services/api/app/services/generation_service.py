from __future__ import annotations

from uuid import uuid4

from packages.provider_sdk.gateway import ProviderGateway
from packages.shared.contracts.assets import AssetCreateRequest, AssetResponse
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
from packages.shared.enums.asset_origin import AssetOrigin
from packages.shared.enums.asset_type import AssetType
from packages.shared.enums.model_capability import ModelCapability
from services.api.app.services.asset_service import InMemoryAssetService
from services.api.app.services.errors import ValidationServiceError
from services.api.app.services.provider_service import InMemoryProviderService


class GenerationService:
    def __init__(
        self,
        *,
        provider_service: InMemoryProviderService,
        asset_service: InMemoryAssetService,
        provider_gateway: ProviderGateway,
    ) -> None:
        self._provider_service = provider_service
        self._asset_service = asset_service
        self._provider_gateway = provider_gateway

    async def generate_image(self, payload: ImageGenerationRequest) -> MediaGenerationResponse:
        provider, _ = self._provider_service.ensure_model_capability(
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
        provider_result = await self._provider_gateway.generate_image(provider, gateway_payload)
        saved_assets = self._save_media_assets(
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

    async def generate_video(self, payload: VideoGenerationRequest) -> MediaGenerationResponse:
        provider, _ = self._provider_service.ensure_model_capability(
            payload.provider_id,
            payload.model,
            ModelCapability.VIDEO,
        )
        image_urls, image_base64 = self._resolve_image_materials(payload.image_material_asset_ids)
        image_urls.extend(payload.image_material_urls)
        scene_prompt_texts = self._resolve_scene_prompt_materials(payload.scene_prompt_asset_ids)
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
        provider_result = await self._provider_gateway.generate_video(provider, gateway_payload)
        saved_assets = self._save_media_assets(
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

    async def generate_text(self, payload: TextGenerationRequest) -> TextGenerationResponse:
        provider, _ = self._provider_service.ensure_model_capability(
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
        provider_result = await self._provider_gateway.generate_text(provider, gateway_payload)
        saved_assets: list[AssetResponse] = []
        if payload.save.enabled:
            saved_assets.append(
                self._asset_service.create_asset(
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
        return TextGenerationResponse(
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

    def _resolve_image_materials(self, asset_ids: list[str]) -> tuple[list[str], list[str]]:
        image_urls: list[str] = []
        image_base64: list[str] = []
        for asset_id in asset_ids:
            asset = self._asset_service.require_asset(asset_id)
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

    def _resolve_scene_prompt_materials(self, asset_ids: list[str]) -> list[str]:
        prompts: list[str] = []
        for asset_id in asset_ids:
            asset = self._asset_service.require_asset(asset_id)
            if asset.asset_type != AssetType.TEXT:
                raise ValidationServiceError("Scene prompt asset must be text type")
            if not asset.content_text:
                raise ValidationServiceError("Scene prompt asset has no text content")
            prompts.append(asset.content_text)
        return prompts

    def _save_media_assets(
        self,
        *,
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
