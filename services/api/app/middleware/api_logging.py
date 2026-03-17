from __future__ import annotations

import json
import logging
import time
from typing import Any
from urllib.parse import parse_qs
from uuid import uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)

_SENSITIVE_KEYS = {
    "password",
    "api_key",
    "authorization",
    "access_token",
    "refresh_token",
    "token",
    "secret",
}

_DEFAULT_MAX_REQUEST_SIZE_BYTES = 10 * 1024 * 1024  # 10 MiB


def _get_header(headers: list[tuple[bytes, bytes]], name: bytes) -> str | None:
    target = name.lower()
    for key, value in headers:
        if key.lower() == target:
            try:
                return value.decode("utf-8")
            except Exception:
                return None
    return None


def _decode_utf8(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except Exception:
        return data.decode("utf-8", errors="replace")


def _truncate_string(value: str, *, limit: int) -> str:
    if len(value) <= limit:
        return value
    return f"{value[:limit]}...(truncated)"


def _sanitize_json(value: Any, *, max_string_len: int, max_items: int) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for idx, (key, item) in enumerate(value.items()):
            if idx >= max_items:
                sanitized["..."] = f"{len(value) - max_items} more keys"
                break
            if key.lower() in _SENSITIVE_KEYS:
                sanitized[key] = "***"
                continue
            sanitized[key] = _sanitize_json(
                item, max_string_len=max_string_len, max_items=max_items
            )
        return sanitized
    if isinstance(value, list):
        trimmed = value[:max_items]
        sanitized_list = [
            _sanitize_json(item, max_string_len=max_string_len, max_items=max_items)
            for item in trimmed
        ]
        if len(value) > max_items:
            sanitized_list.append(f"... {len(value) - max_items} more items")
        return sanitized_list
    if isinstance(value, str):
        return _truncate_string(value, limit=max_string_len)
    return value


def _json_preview(
    raw: bytes, *, max_bytes: int, max_string_len: int, max_items: int
) -> dict[str, Any] | None:
    if not raw:
        return None
    preview = raw[:max_bytes]
    try:
        data = json.loads(_decode_utf8(preview))
    except Exception:
        return {"_raw": _truncate_string(_decode_utf8(preview), limit=max_bytes)}
    return _sanitize_json(data, max_string_len=max_string_len, max_items=max_items)


class _RequestBodyTooLarge(Exception):
    pass


class ApiLoggingMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        max_request_body_bytes: int = 16_384,
        max_response_body_bytes: int = 16_384,
        max_request_size_bytes: int = _DEFAULT_MAX_REQUEST_SIZE_BYTES,
        max_string_len: int = 600,
        max_items: int = 60,
        skip_paths: set[str] | None = None,
    ) -> None:
        self._app = app
        self._max_request_body_bytes = max_request_body_bytes
        self._max_response_body_bytes = max_response_body_bytes
        self._max_request_size_bytes = max_request_size_bytes
        self._max_string_len = max_string_len
        self._max_items = max_items
        self._skip_paths = skip_paths or set()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        path = scope.get("path") or ""
        if path in self._skip_paths:
            await self._app(scope, receive, send)
            return

        request_id = uuid4().hex[:12]
        start = time.monotonic()

        request_headers = scope.get("headers") or []
        method = scope.get("method") or ""
        query_string = _decode_utf8(scope.get("query_string") or b"")
        query_params = parse_qs(query_string, keep_blank_values=True) if query_string else {}
        request_content_type = _get_header(request_headers, b"content-type") or ""
        user_agent = _get_header(request_headers, b"user-agent")

        request_body_preview = bytearray()
        request_body_len = 0
        response_started = False

        async def receive_wrapper() -> Message:
            nonlocal request_body_len
            message = await receive()
            if message["type"] != "http.request":
                return message

            chunk = message.get("body") or b""
            request_body_len += len(chunk)
            if (
                chunk
                and self._max_request_body_bytes > 0
                and len(request_body_preview) < self._max_request_body_bytes
            ):
                remaining = self._max_request_body_bytes - len(request_body_preview)
                request_body_preview.extend(chunk[:remaining])

            if self._max_request_size_bytes > 0 and request_body_len > self._max_request_size_bytes:
                raise _RequestBodyTooLarge()

            return message

        status_code: int | None = None
        response_content_type: str | None = None
        response_body_preview = bytearray()
        response_body_len = 0

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code, response_content_type, response_body_len, response_started

            if message["type"] == "http.response.start":
                response_started = True
                status_code = int(message["status"])
                headers = list(message.get("headers") or [])
                headers.append((b"x-request-id", request_id.encode("utf-8")))
                message["headers"] = headers
                response_content_type = _get_header(headers, b"content-type")

            if message["type"] == "http.response.body":
                chunk = message.get("body", b"")
                response_body_len += len(chunk)
                if len(response_body_preview) < self._max_response_body_bytes:
                    remaining = self._max_response_body_bytes - len(response_body_preview)
                    response_body_preview.extend(chunk[:remaining])

                if not message.get("more_body", False):
                    duration_ms = int((time.monotonic() - start) * 1000)
                    request_body_preview_truncated = request_body_len > len(request_body_preview)
                    request_json = (
                        _json_preview(
                            bytes(request_body_preview),
                            max_bytes=self._max_request_body_bytes,
                            max_string_len=self._max_string_len,
                            max_items=self._max_items,
                        )
                        if "application/json" in request_content_type
                        else None
                    )
                    response_json = (
                        _json_preview(
                            bytes(response_body_preview),
                            max_bytes=self._max_response_body_bytes,
                            max_string_len=self._max_string_len,
                            max_items=self._max_items,
                        )
                        if (response_content_type and "application/json" in response_content_type)
                        else None
                    )

                    log_payload = {
                        "request_id": request_id,
                        "method": method,
                        "path": path,
                        "query": _sanitize_json(
                            query_params,
                            max_string_len=self._max_string_len,
                            max_items=self._max_items,
                        ),
                        "status_code": status_code,
                        "duration_ms": duration_ms,
                        "request": {
                            "content_type": request_content_type,
                            "body_len": request_body_len,
                            "body_preview_truncated": request_body_preview_truncated,
                            "json": request_json,
                        },
                        "response": {
                            "content_type": response_content_type,
                            "body_len": response_body_len,
                            "json": response_json,
                        },
                        "client": {"user_agent": user_agent},
                        "auth": {
                            "has_bearer_token": bool(_get_header(request_headers, b"authorization")),
                        },
                    }
                    if status_code is not None and status_code >= 400:
                        logger.warning("api_call: %s", log_payload)
                    else:
                        logger.info("api_call: %s", log_payload)

            await send(message)

        try:
            await self._app(scope, receive_wrapper, send_wrapper)
        except _RequestBodyTooLarge:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.warning(
                "api_call_request_too_large: %s",
                {
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "query": _sanitize_json(
                        query_params,
                        max_string_len=self._max_string_len,
                        max_items=self._max_items,
                    ),
                    "duration_ms": duration_ms,
                    "request_body_len": request_body_len,
                    "max_request_size_bytes": self._max_request_size_bytes,
                },
            )
            if response_started:
                raise

            headers = [
                (b"content-type", b"application/json"),
                (b"x-request-id", request_id.encode("utf-8")),
            ]
            await send({"type": "http.response.start", "status": 413, "headers": headers})
            await send(
                {
                    "type": "http.response.body",
                    "body": b'{"detail":"Request body too large"}',
                    "more_body": False,
                }
            )
        except Exception:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.exception(
                "api_call_unhandled_error: %s",
                {
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "query": _sanitize_json(
                        query_params,
                        max_string_len=self._max_string_len,
                        max_items=self._max_items,
                    ),
                    "duration_ms": duration_ms,
                    "request_body_len": request_body_len,
                },
            )
            raise
