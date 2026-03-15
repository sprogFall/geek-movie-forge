from __future__ import annotations

import logging
import os
import time
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

logger = logging.getLogger(__name__)


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
        url = _resolve_endpoint_url(str(provider.base_url), endpoint.path)
        headers = {"Authorization": f"Bearer {provider.api_key}"}
        log_body = _env_flag("GMF_LOG_PROVIDER_BODY", default=False)
        start = time.monotonic()
        response: httpx.Response | None = None
        try:
            logger.info(
                "Provider request: provider_id=%s provider_name=%s url=%s timeout=%.1fs keys=%s",
                provider.provider_id,
                provider.name,
                url,
                endpoint.timeout_seconds,
                sorted(body.keys()),
            )
            if log_body:
                logger.info(
                    "Provider request body: provider_id=%s url=%s body=%s",
                    provider.provider_id,
                    url,
                    _summarize_body(body),
                )
            async with httpx.AsyncClient(
                headers=headers,
                timeout=endpoint.timeout_seconds,
                transport=self._transport,
            ) as client:
                response = await client.post(url, json=body)
                response.raise_for_status()
                parsed = response.json()
                duration_ms = int((time.monotonic() - start) * 1000)
                logger.info(
                    "Provider response: provider_id=%s url=%s status=%s duration_ms=%s",
                    provider.provider_id,
                    url,
                    response.status_code,
                    duration_ms,
                )
                if log_body:
                    logger.info(
                        "Provider response body: provider_id=%s url=%s body=%s",
                        provider.provider_id,
                        url,
                        _summarize_body(parsed),
                    )
                return parsed
        except httpx.HTTPStatusError as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            detail = _format_http_status_error(exc)
            if exc.response.status_code == 404:
                detail = f"{detail}. Check provider base_url and routes.*.path configuration"
            elif exc.response.status_code in (401, 403):
                detail = f"{detail}. Check provider api_key and permissions"
            logger.warning(
                "Provider HTTP error: provider_id=%s url=%s duration_ms=%s detail=%s",
                provider.provider_id,
                url,
                duration_ms,
                detail,
            )
            raise UpstreamServiceError(detail) from exc
        except httpx.RequestError as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            url = str(getattr(exc, "request", None).url) if getattr(exc, "request", None) else None
            detail = f"Provider request failed: {exc}"
            if url:
                detail = f"{detail} at {url}"
            logger.warning(
                "Provider request error: provider_id=%s duration_ms=%s detail=%s",
                provider.provider_id,
                duration_ms,
                detail,
            )
            raise UpstreamServiceError(detail) from exc
        except ValueError as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            detail = "Provider returned invalid JSON"
            if response is not None:
                detail = f"{detail} at {response.request.method} {response.request.url}"
                body_text = _truncate_text(response.text)
                if body_text:
                    detail = f"{detail}: {body_text}"
            logger.warning(
                "Provider response parse error: provider_id=%s url=%s duration_ms=%s detail=%s",
                provider.provider_id,
                url,
                duration_ms,
                detail,
            )
            raise UpstreamServiceError(detail) from exc

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


def _truncate_text(text: str, *, limit: int = 500) -> str | None:
    value = (text or "").strip()
    if not value:
        return None
    if len(value) <= limit:
        return value
    return f"{value[:limit]}..."


def _format_http_status_error(exc: httpx.HTTPStatusError) -> str:
    response = exc.response
    request = exc.request
    reason = response.reason_phrase
    base = f"Provider request failed with status {response.status_code}"
    if reason:
        base = f"{base} ({reason})"
    base = f"{base} at {request.method} {request.url}"
    body_text = _truncate_text(response.text)
    if body_text:
        return f"{base}: {body_text}"
    return base


def _env_flag(name: str, *, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _resolve_endpoint_url(base_url: str, path: str) -> str:
    value = (path or "").strip()
    if value.startswith(("http://", "https://")):
        return value

    base = base_url.rstrip("/")
    rel = value.lstrip("/")
    if not rel:
        return base

    # Allow base_url to be configured as a full endpoint URL without duplicating the route path.
    if base.endswith("/" + rel) or base.endswith(rel):
        return base
    return f"{base}/{rel}"


def _summarize_body(value: Any) -> Any:
    if isinstance(value, dict):
        summarized: dict[str, Any] = {}
        for key, item in value.items():
            if isinstance(item, str):
                if "base64" in key:
                    summarized[key] = f"<base64:{len(item)} chars>"
                elif key in ("prompt", "custom_prompt", "preset_prompt", "source_text"):
                    summarized[key] = _truncate_text(item, limit=200)
                    summarized[f"{key}_len"] = len(item)
                else:
                    summarized[key] = _truncate_text(item, limit=200)
                continue

            if isinstance(item, list) and "base64" in key:
                summarized[key] = f"<base64_list:{len(item)} items>"
                continue

            if isinstance(item, list) and key in ("image_material_urls", "scene_prompt_texts", "outputs", "data"):
                summarized[key] = f"<list:{len(item)} items>"
                continue

            if isinstance(item, dict) and key == "options":
                summarized[key] = {"keys": sorted(item.keys())}
                continue

            summarized[key] = item
        return summarized

    if isinstance(value, list):
        return f"<list:{len(value)} items>"

    if isinstance(value, str):
        return _truncate_text(value, limit=200)

    return value
