from __future__ import annotations

from typing import Any, Protocol

import httpx

from packages.shared.contracts.generations import (
    GeneratedMediaOutput,
    ImageGenerationPayload,
    ProviderMediaGenerationResult,
    ProviderTextGenerationResult,
    TextGenerationPayload,
    VideoGenerationPayload,
)
from packages.shared.contracts.providers import ProviderEndpointConfig, ProviderRecord
from services.api.app.services.errors import UpstreamServiceError


class ProviderGateway(Protocol):
    async def generate_image(
        self,
        provider: ProviderRecord,
        payload: ImageGenerationPayload,
    ) -> ProviderMediaGenerationResult: ...

    async def generate_video(
        self,
        provider: ProviderRecord,
        payload: VideoGenerationPayload,
    ) -> ProviderMediaGenerationResult: ...

    async def generate_text(
        self,
        provider: ProviderRecord,
        payload: TextGenerationPayload,
    ) -> ProviderTextGenerationResult: ...


class HttpProviderGateway:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport

    async def generate_image(
        self,
        provider: ProviderRecord,
        payload: ImageGenerationPayload,
    ) -> ProviderMediaGenerationResult:
        body = {
            "model": payload.model,
            "count": payload.count,
            "prompt": payload.resolved_prompt,
            "custom_prompt": payload.prompt,
            "preset_prompt": payload.preset_prompt,
            "options": payload.options,
        }
        response = await self._post(provider, provider.routes.image, body)
        return self._parse_media_result(response)

    async def generate_video(
        self,
        provider: ProviderRecord,
        payload: VideoGenerationPayload,
    ) -> ProviderMediaGenerationResult:
        body = {
            "model": payload.model,
            "count": payload.count,
            "prompt": payload.resolved_prompt,
            "custom_prompt": payload.prompt,
            "preset_prompt": payload.preset_prompt,
            "image_material_urls": payload.image_material_urls,
            "image_material_base64": payload.image_material_base64,
            "scene_prompt_texts": payload.scene_prompt_texts,
            "options": payload.options,
        }
        response = await self._post(provider, provider.routes.video, body)
        return self._parse_media_result(response)

    async def generate_text(
        self,
        provider: ProviderRecord,
        payload: TextGenerationPayload,
    ) -> ProviderTextGenerationResult:
        body = {
            "model": payload.model,
            "task_type": payload.task_type,
            "source_text": payload.source_text,
            "prompt": payload.resolved_prompt,
            "custom_prompt": payload.prompt,
            "preset_prompt": payload.preset_prompt,
            "options": payload.options,
        }
        response = await self._post(provider, provider.routes.text, body)
        return self._parse_text_result(response)

    async def _post(
        self,
        provider: ProviderRecord,
        endpoint: ProviderEndpointConfig,
        body: dict[str, Any],
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {provider.api_key}"}
        try:
            async with httpx.AsyncClient(
                base_url=str(provider.base_url),
                headers=headers,
                timeout=endpoint.timeout_seconds,
                transport=self._transport,
            ) as client:
                response = await client.post(endpoint.path, json=body)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            raise UpstreamServiceError(
                f"Provider request failed with status {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            raise UpstreamServiceError("Provider request failed") from exc
        except ValueError as exc:
            raise UpstreamServiceError("Provider returned invalid JSON") from exc

    def _parse_media_result(self, body: dict[str, Any]) -> ProviderMediaGenerationResult:
        raw_outputs = body.get("outputs")
        if raw_outputs is None and isinstance(body.get("data"), list):
            raw_outputs = body["data"]
        if raw_outputs is None and any(key in body for key in ("url", "b64_json", "base64_data")):
            raw_outputs = [body]
        outputs = [
            GeneratedMediaOutput(
                index=item.get("index", index),
                url=item.get("url"),
                base64_data=item.get("base64_data") or item.get("b64_json"),
                mime_type=item.get("mime_type") or item.get("content_type"),
                text=item.get("text"),
                cover_image_url=item.get("cover_image_url"),
                duration_seconds=item.get("duration_seconds"),
                metadata=item.get("metadata") or {},
            )
            for index, item in enumerate(raw_outputs or [])
        ]
        return ProviderMediaGenerationResult(
            provider_request_id=body.get("provider_request_id") or body.get("request_id"),
            outputs=outputs,
        )

    def _parse_text_result(self, body: dict[str, Any]) -> ProviderTextGenerationResult:
        output_text = body.get("output_text") or body.get("text") or body.get("content")
        if output_text is None:
            outputs = body.get("outputs") or body.get("data") or []
            first_item = outputs[0] if outputs else {}
            output_text = first_item.get("text") or first_item.get("content")
        if not output_text:
            raise UpstreamServiceError("Provider response missing text output")
        return ProviderTextGenerationResult(
            provider_request_id=body.get("provider_request_id") or body.get("request_id"),
            output_text=output_text,
            metadata=body.get("metadata") or {},
        )
