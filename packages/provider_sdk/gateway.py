from __future__ import annotations

import asyncio
import ipaddress
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
from services.api.app.services.errors import UpstreamServiceError, ValidationServiceError

logger = logging.getLogger(__name__)

_VOLCENGINE_VIDEO_TERMINAL_STATUS = {"cancelled", "failed", "expired", "succeeded"}
_VOLCENGINE_VIDEO_RUNNING_STATUS = {"queued", "running"}
_VOLCENGINE_VIDEO_OPTION_KEYS = (
    "callback_url",
    "return_last_frame",
    "service_tier",
    "execution_expires_after",
    "generate_audio",
    "draft",
    "resolution",
    "ratio",
    "duration",
    "frames",
    "seed",
    "camera_fixed",
    "watermark",
)


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
        if provider.adapter_type == "modelscope":
            return await self._generate_modelscope_image(provider, provider.routes.image, body)
        response = await self._post(provider, provider.routes.image, body)
        return self._parse_media_result(response)

    async def generate_video(
        self,
        provider: ProviderRecord,
        payload: VideoGenerationPayload,
    ) -> ProviderMediaGenerationResult:
        if provider.adapter_type == "volcengine_ark":
            return await self._generate_volcengine_video(provider, provider.routes.video, payload)
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
        url = _resolve_endpoint_url(str(provider.base_url), provider.routes.text.path)
        body = _build_text_request_body(url, payload)
        response = await self._post(provider, provider.routes.text, body, url=url)
        return self._parse_text_result(response)

    async def _post(
        self,
        provider: ProviderRecord,
        endpoint: ProviderEndpointConfig,
        body: dict[str, Any],
        *,
        url: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        url = url or _resolve_endpoint_url(str(provider.base_url), endpoint.path)
        return await self._request_json(
            method="POST",
            provider=provider,
            endpoint=endpoint,
            url=url,
            body=body,
            headers=headers,
        )

    async def _get(
        self,
        provider: ProviderRecord,
        endpoint: ProviderEndpointConfig,
        *,
        url: str,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        return await self._request_json(
            method="GET",
            provider=provider,
            endpoint=endpoint,
            url=url,
            headers=headers,
        )

    async def _request_json(
        self,
        *,
        method: str,
        provider: ProviderRecord,
        endpoint: ProviderEndpointConfig,
        url: str,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        _ensure_outbound_provider_url_is_allowed(url)
        request_headers = _build_request_headers(provider.api_key, headers)
        log_body = _env_flag("GMF_LOG_PROVIDER_BODY", default=False)
        start = time.monotonic()
        response: httpx.Response | None = None
        try:
            logger.info(
                "Provider request: provider_id=%s provider_name=%s method=%s url=%s timeout=%.1fs keys=%s",
                provider.provider_id,
                provider.name,
                method,
                url,
                endpoint.timeout_seconds,
                sorted(body.keys()) if body else [],
            )
            if log_body and body is not None:
                logger.info(
                    "Provider request body: provider_id=%s url=%s body=%s",
                    provider.provider_id,
                    url,
                    _summarize_body(body),
                )
            async with httpx.AsyncClient(
                headers=request_headers,
                timeout=endpoint.timeout_seconds,
                transport=self._transport,
            ) as client:
                response = await client.request(method, url, json=body)
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

    async def _generate_modelscope_image(
        self,
        provider: ProviderRecord,
        endpoint: ProviderEndpointConfig,
        body: dict[str, Any],
    ) -> ProviderMediaGenerationResult:
        submit_url = _resolve_endpoint_url(str(provider.base_url), endpoint.path)
        submit_result = await self._post(
            provider,
            endpoint,
            body,
            url=submit_url,
            headers={"X-ModelScope-Async-Mode": "true"},
        )
        task_id = submit_result.get("task_id")
        if not isinstance(task_id, str) or not task_id.strip():
            raise UpstreamServiceError("ModelScope image generation response missing task_id")

        poll_url = _resolve_modelscope_task_url(str(provider.base_url), task_id)
        deadline = time.monotonic() + endpoint.timeout_seconds
        while True:
            task_result = await self._get(
                provider,
                endpoint,
                url=poll_url,
                headers={"X-ModelScope-Task-Type": "image_generation"},
            )
            task_status = str(task_result.get("task_status") or "").upper()
            if task_status == "SUCCEED":
                return _parse_modelscope_image_result(task_id, task_result)
            if task_status in {"FAILED", "CANCELED", "CANCELLED"}:
                detail = _extract_modelscope_error_message(task_result)
                if not detail:
                    detail = f"ModelScope image generation ended with status {task_status}"
                raise UpstreamServiceError(detail)
            if time.monotonic() >= deadline:
                raise UpstreamServiceError(
                    f"ModelScope image generation timed out while waiting for task {task_id}"
                )
            await asyncio.sleep(1.0)

    async def _generate_volcengine_video(
        self,
        provider: ProviderRecord,
        endpoint: ProviderEndpointConfig,
        payload: VideoGenerationPayload,
    ) -> ProviderMediaGenerationResult:
        submit_url = _resolve_endpoint_url(str(provider.base_url), endpoint.path)
        submit_body = _build_volcengine_video_request_body(payload)
        submit_result = await self._post(provider, endpoint, submit_body, url=submit_url)
        task_id = submit_result.get("id") or submit_result.get("task_id")
        if not isinstance(task_id, str) or not task_id.strip():
            detail = _extract_volcengine_error_message(submit_result)
            if detail:
                raise UpstreamServiceError(detail)
            raise UpstreamServiceError("Volcengine video generation response missing task id")

        poll_url = _resolve_volcengine_task_url(str(provider.base_url), task_id)
        deadline = time.monotonic() + endpoint.timeout_seconds
        while True:
            task_result = await self._get(provider, endpoint, url=poll_url)
            task_status = str(task_result.get("status") or "").strip().lower()
            if task_status == "succeeded":
                return _parse_volcengine_video_result(task_id, task_result)
            if task_status in _VOLCENGINE_VIDEO_TERMINAL_STATUS:
                detail = _extract_volcengine_error_message(task_result)
                if not detail:
                    detail = f"Volcengine video generation ended with status {task_status}"
                raise UpstreamServiceError(detail)
            if task_status and task_status not in _VOLCENGINE_VIDEO_RUNNING_STATUS:
                raise UpstreamServiceError(
                    f"Volcengine video generation returned unknown status {task_status}"
                )
            if time.monotonic() >= deadline:
                raise UpstreamServiceError(
                    f"Volcengine video generation timed out while waiting for task {task_id}"
                )
            await asyncio.sleep(1.0)

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
        if isinstance(body.get("choices"), list):
            output_text = _extract_openai_choice_text(body["choices"])
            if output_text:
                metadata = body.get("metadata") or {}
                if isinstance(body.get("usage"), dict):
                    metadata = {**metadata, "usage": body["usage"]}
                return ProviderTextGenerationResult(
                    provider_request_id=body.get("provider_request_id")
                    or body.get("request_id")
                    or body.get("id"),
                    output_text=output_text,
                    metadata=metadata,
                )

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


def _app_env() -> str:
    return (os.getenv("APP_ENV") or "local").strip().lower()


def _allow_private_provider_urls() -> bool:
    return _env_flag(
        "GMF_ALLOW_PRIVATE_PROVIDER_URLS",
        default=_app_env() in ("local", "test"),
    )


def _allow_insecure_http_provider_urls() -> bool:
    return _env_flag(
        "GMF_ALLOW_INSECURE_HTTP_PROVIDER_URLS",
        default=_app_env() in ("local", "test"),
    )


def _ensure_outbound_provider_url_is_allowed(url: str) -> None:
    parsed = httpx.URL(url)
    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        raise ValidationServiceError("Provider URL must use http or https")
    if scheme == "http" and not _allow_insecure_http_provider_urls():
        raise ValidationServiceError(
            "Insecure http provider URLs are disabled. Use https or set GMF_ALLOW_INSECURE_HTTP_PROVIDER_URLS=true"
        )
    if parsed.username or parsed.password:
        raise ValidationServiceError("Provider URL must not contain username/password")

    host = parsed.host
    if not host:
        raise ValidationServiceError("Provider URL is missing host")
    normalized_host = host.strip().lower().rstrip(".")

    allow_private = _allow_private_provider_urls()
    if normalized_host in {"localhost"} or normalized_host.endswith(".localhost"):
        if not allow_private:
            raise ValidationServiceError(
                "Provider URL points to localhost which is blocked. Set GMF_ALLOW_PRIVATE_PROVIDER_URLS=true to override"
            )
        return

    try:
        ip = ipaddress.ip_address(normalized_host)
    except ValueError:
        return

    if ip.is_link_local:
        raise ValidationServiceError("Provider URL points to a link-local address which is not allowed")
    if ip.is_multicast:
        raise ValidationServiceError("Provider URL points to a multicast address which is not allowed")
    if ip.is_unspecified:
        raise ValidationServiceError("Provider URL points to an unspecified address which is not allowed")
    if ip.is_reserved:
        raise ValidationServiceError("Provider URL points to a reserved address which is not allowed")
    if (ip.is_loopback or ip.is_private) and not allow_private:
        raise ValidationServiceError(
            "Provider URL points to a private/loopback address which is blocked. Set GMF_ALLOW_PRIVATE_PROVIDER_URLS=true to override"
        )


def _build_request_headers(
    api_key: str,
    extra_headers: dict[str, str] | None = None,
) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {api_key}"}
    if extra_headers:
        headers.update(extra_headers)
    return headers


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


def _resolve_modelscope_task_url(base_url: str, task_id: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/v1"):
        return f"{base}/tasks/{task_id}"
    return _resolve_endpoint_url(base_url, f"/v1/tasks/{task_id}")


def _resolve_volcengine_task_url(base_url: str, task_id: str) -> str:
    return _resolve_endpoint_url(base_url, f"/contents/generations/tasks/{task_id}")


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

            if isinstance(item, list) and key in (
                "content",
                "image_material_urls",
                "image_materials",
                "scene_prompt_texts",
                "outputs",
                "data",
            ):
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


def _parse_modelscope_image_result(
    task_id: str,
    body: dict[str, Any],
) -> ProviderMediaGenerationResult:
    raw_outputs = body.get("output_images") or body.get("images") or []
    outputs: list[GeneratedMediaOutput] = []
    for index, item in enumerate(raw_outputs):
        if isinstance(item, str):
            outputs.append(GeneratedMediaOutput(index=index, url=item))
            continue
        if isinstance(item, dict):
            outputs.append(
                GeneratedMediaOutput(
                    index=item.get("index", index),
                    url=item.get("url") or item.get("image_url"),
                    base64_data=item.get("base64_data") or item.get("b64_json"),
                    mime_type=item.get("mime_type") or item.get("content_type"),
                    metadata=item.get("metadata") or {},
                )
            )
    if not outputs:
        raise UpstreamServiceError("ModelScope image generation succeeded but returned no images")
    return ProviderMediaGenerationResult(provider_request_id=task_id, outputs=outputs)


def _extract_modelscope_error_message(body: dict[str, Any]) -> str | None:
    errors = body.get("errors")
    if isinstance(errors, dict):
        for key in ("message", "detail", "error"):
            value = errors.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    for key in ("message", "detail", "error_message"):
        value = body.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _build_volcengine_video_request_body(payload: VideoGenerationPayload) -> dict[str, Any]:
    if payload.count != 1:
        raise ValidationServiceError("Volcengine Ark video generation requires count=1")
    if payload.options.get("frames") is not None:
        raise ValidationServiceError("Volcengine Seedance 1.5 Pro does not support frames")

    content: list[dict[str, Any]] = []
    if payload.resolved_prompt:
        content.append({"type": "text", "text": payload.resolved_prompt})

    draft_task_id = str(payload.options.get("draft_task_id") or "").strip()
    if draft_task_id:
        content.append({"type": "draft_task", "draft_task": {"id": draft_task_id}})

    content.extend(_build_volcengine_image_content(payload))
    if not content:
        raise ValidationServiceError(
            "Volcengine video generation requires prompt, image materials, or draft_task_id"
        )

    body: dict[str, Any] = {"model": payload.model, "content": content}
    for key in _VOLCENGINE_VIDEO_OPTION_KEYS:
        if key in payload.options:
            body[key] = payload.options[key]
    return body


def _build_volcengine_image_content(payload: VideoGenerationPayload) -> list[dict[str, Any]]:
    materials = _coerce_volcengine_input_materials(payload)
    input_mode = str(payload.options.get("input_mode") or "").strip().lower()
    if input_mode == "reference_image" or len(materials) > 2:
        raise ValidationServiceError(
            "Volcengine Seedance 1.5 Pro does not support reference-image mode; use one first frame or two first/last frames"
        )
    if input_mode == "first_last_frame" and len(materials) != 2:
        raise ValidationServiceError("Volcengine first/last-frame mode requires exactly 2 images")
    if input_mode == "first_frame" and len(materials) != 1:
        raise ValidationServiceError("Volcengine first-frame mode requires exactly 1 image")

    items: list[dict[str, Any]] = []
    for index, item in enumerate(materials):
        role = "first_frame" if index == 0 else "last_frame"
        items.append(
            {
                "type": "image_url",
                "role": role,
                "image_url": {"url": _normalize_volcengine_image_url(item)},
            }
        )
    return items


def _coerce_volcengine_input_materials(payload: VideoGenerationPayload) -> list[Any]:
    if payload.image_materials:
        return payload.image_materials

    materials: list[dict[str, str]] = []
    for value in payload.image_material_urls:
        materials.append({"kind": "url", "value": value})
    for value in payload.image_material_base64:
        materials.append({"kind": "base64", "value": value})
    return materials


def _normalize_volcengine_image_url(item: Any) -> str:
    if hasattr(item, "kind"):
        kind = str(item.kind)
        value = str(item.value)
    elif isinstance(item, dict):
        kind = str(item.get("kind") or "")
        value = str(item.get("value") or "")
    else:
        raise ValidationServiceError("Volcengine image material must be a url/base64 object")

    normalized_value = value.strip()
    if not normalized_value:
        raise ValidationServiceError("Volcengine image material value cannot be empty")
    if kind == "url":
        return normalized_value
    if kind == "base64":
        if normalized_value.startswith("data:"):
            return normalized_value
        return f"data:image/png;base64,{normalized_value}"
    raise ValidationServiceError(f"Unsupported Volcengine image material kind: {kind}")


def _parse_volcengine_video_result(
    task_id: str,
    body: dict[str, Any],
) -> ProviderMediaGenerationResult:
    content = body.get("content")
    if not isinstance(content, dict):
        raise UpstreamServiceError(
            "Volcengine video generation succeeded but returned invalid content payload"
        )

    video_url = content.get("video_url")
    if not isinstance(video_url, str) or not video_url.strip():
        raise UpstreamServiceError(
            "Volcengine video generation succeeded but returned no video_url"
        )

    metadata = {
        key: value
        for key, value in body.items()
        if key
        in {
            "model",
            "status",
            "seed",
            "resolution",
            "ratio",
            "duration",
            "frames",
            "usage",
            "created_at",
            "updated_at",
        }
    }
    return ProviderMediaGenerationResult(
        provider_request_id=task_id,
        outputs=[
            GeneratedMediaOutput(
                index=0,
                url=video_url.strip(),
                mime_type="video/mp4",
                cover_image_url=_string_or_none(content.get("last_frame_url")),
                duration_seconds=_float_or_none(body.get("duration")),
                metadata=metadata,
            )
        ],
    )


def _extract_volcengine_error_message(body: dict[str, Any]) -> str | None:
    error = body.get("error")
    if isinstance(error, dict):
        code = _string_or_none(error.get("code"))
        message = _string_or_none(error.get("message") or error.get("detail"))
        if code and message:
            return f"{code}: {message}"
        if message:
            return message
        if code:
            return code
    if isinstance(error, str) and error.strip():
        return error.strip()

    task_id = _string_or_none(body.get("id"))
    status = _string_or_none(body.get("status"))
    for key in ("message", "detail"):
        value = _string_or_none(body.get(key))
        if value:
            if task_id and status:
                return f"Volcengine task {task_id} {status}: {value}"
            return value
    if task_id and status and status in {"cancelled", "failed", "expired"}:
        return f"Volcengine task {task_id} ended with status {status}"
    return None


def _string_or_none(value: Any) -> str | None:
    if isinstance(value, str):
        normalized = value.strip()
        if normalized:
            return normalized
    return None


def _float_or_none(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _build_text_request_body(url: str, payload: TextGenerationPayload) -> dict[str, Any]:
    if _is_openai_chat_endpoint(url):
        body = {
            key: value
            for key, value in payload.options.items()
            if key not in {"model", "messages", "stream"}
        }
        body["model"] = payload.model
        body["messages"] = _build_openai_messages(payload)
        body["stream"] = False
        return body

    return {
        "model": payload.model,
        "task_type": payload.task_type,
        "source_text": payload.source_text,
        "prompt": payload.resolved_prompt,
        "custom_prompt": payload.prompt,
        "preset_prompt": payload.preset_prompt,
        "options": payload.options,
    }


def _is_openai_chat_endpoint(url: str) -> bool:
    return url.rstrip("/").endswith("/chat/completions")


def _build_openai_messages(payload: TextGenerationPayload) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    if payload.resolved_prompt:
        messages.append({"role": "system", "content": payload.resolved_prompt})

    user_parts = [f"Task type: {payload.task_type}", "", "Source text:", payload.source_text]
    messages.append({"role": "user", "content": "\n".join(user_parts)})
    return messages


def _extract_openai_choice_text(choices: list[Any]) -> str | None:
    if not choices:
        return None

    first_choice = choices[0] or {}
    message = first_choice.get("message") if isinstance(first_choice, dict) else None
    if isinstance(message, dict):
        content = message.get("content")
        text = _coerce_openai_content_to_text(content)
        if text:
            return text

    if isinstance(first_choice, dict):
        content = first_choice.get("text")
        if isinstance(content, str) and content.strip():
            return content
    return None


def _coerce_openai_content_to_text(content: Any) -> str | None:
    if isinstance(content, str):
        return content.strip() or None

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                if item.strip():
                    parts.append(item.strip())
                continue
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())
        if parts:
            return "\n".join(parts)
    return None
