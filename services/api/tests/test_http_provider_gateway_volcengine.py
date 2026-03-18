from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime

import httpx
import pytest

from packages.provider_sdk.gateway import HttpProviderGateway
from packages.shared.contracts.generations import (
    VideoGenerationPayload,
    VideoInputMaterial,
)
from packages.shared.contracts.providers import ProviderModelConfig, ProviderRecord, ProviderRoutes
from packages.shared.enums.model_capability import ModelCapability
from services.api.app.services.errors import UpstreamServiceError, ValidationServiceError


def _provider_record(
    *,
    base_url: str = "https://ark.cn-beijing.volces.com/api/v3",
) -> ProviderRecord:
    now = datetime.now(UTC)
    return ProviderRecord(
        provider_id="provider_test",
        owner_id="user_test",
        name="Volcengine Ark",
        base_url=base_url,
        api_key="secret",
        adapter_type="volcengine_ark",
        models=[
            ProviderModelConfig(
                model="doubao-seedance-1-5-pro-251215",
                capabilities=[ModelCapability.VIDEO],
            )
        ],
        routes=ProviderRoutes(
            video={"path": "/contents/generations/tasks", "timeout_seconds": 30.0},
        ),
        created_at=now,
        updated_at=now,
    )


def test_http_provider_gateway_volcengine_text_to_video_polls_until_success() -> None:
    requests_seen: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests_seen.append((request.method, str(request.url)))
        if request.method == "POST":
            assert str(request.url) == "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks"
            assert request.headers["Authorization"] == "Bearer secret"
            body = json.loads(request.content.decode("utf-8"))
            assert body == {
                "model": "doubao-seedance-1-5-pro-251215",
                "content": [{"type": "text", "text": "A golden cat yawns at the camera."}],
                "return_last_frame": True,
                "generate_audio": False,
                "resolution": "720p",
                "ratio": "16:9",
                "duration": 5,
                "seed": 11,
                "camera_fixed": False,
                "watermark": True,
            }
            return httpx.Response(200, json={"id": "cgt_123"}, request=request)

        assert str(request.url) == "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks/cgt_123"
        return httpx.Response(
            200,
            json={
                "id": "cgt_123",
                "model": "doubao-seedance-1-5-pro-251215",
                "status": "succeeded",
                "duration": 5,
                "resolution": "720p",
                "ratio": "16:9",
                "usage": {"completion_tokens": 321, "total_tokens": 321},
                "content": {
                    "video_url": "https://cdn.example.com/generated/video.mp4",
                    "last_frame_url": "https://cdn.example.com/generated/last-frame.png",
                },
            },
            request=request,
        )

    transport = httpx.MockTransport(handler)
    gateway = HttpProviderGateway(transport=transport)
    provider = _provider_record()
    payload = VideoGenerationPayload(
        provider_id=provider.provider_id,
        model="doubao-seedance-1-5-pro-251215",
        count=1,
        resolved_prompt="A golden cat yawns at the camera.",
        options={
            "return_last_frame": True,
            "generate_audio": False,
            "resolution": "720p",
            "ratio": "16:9",
            "duration": 5,
            "seed": 11,
            "camera_fixed": False,
            "watermark": True,
        },
    )

    result = asyncio.run(gateway.generate_video(provider, payload))
    assert requests_seen == [
        ("POST", "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks"),
        ("GET", "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks/cgt_123"),
    ]
    assert result.provider_request_id == "cgt_123"
    assert result.outputs[0].url == "https://cdn.example.com/generated/video.mp4"
    assert result.outputs[0].cover_image_url == "https://cdn.example.com/generated/last-frame.png"
    assert result.outputs[0].duration_seconds == 5
    assert result.outputs[0].mime_type == "video/mp4"
    assert result.outputs[0].metadata["usage"]["total_tokens"] == 321


def test_http_provider_gateway_volcengine_first_and_last_frame_maps_image_roles() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            body = json.loads(request.content.decode("utf-8"))
            assert body["content"] == [
                {"type": "text", "text": "The runner crosses the finish line."},
                {
                    "type": "image_url",
                    "role": "first_frame",
                    "image_url": {"url": "https://cdn.example.com/first-frame.png"},
                },
                {
                    "type": "image_url",
                    "role": "last_frame",
                    "image_url": {"url": "data:image/png;base64,ZmFrZQ=="},
                },
            ]
            return httpx.Response(200, json={"id": "cgt_456"}, request=request)

        return httpx.Response(
            200,
            json={
                "id": "cgt_456",
                "status": "succeeded",
                "content": {"video_url": "https://cdn.example.com/generated/finish.mp4"},
            },
            request=request,
        )

    transport = httpx.MockTransport(handler)
    gateway = HttpProviderGateway(transport=transport)
    provider = _provider_record()
    payload = VideoGenerationPayload(
        provider_id=provider.provider_id,
        model="doubao-seedance-1-5-pro-251215",
        count=1,
        resolved_prompt="The runner crosses the finish line.",
        image_materials=[
            VideoInputMaterial(kind="url", value="https://cdn.example.com/first-frame.png"),
            VideoInputMaterial(kind="base64", value="data:image/png;base64,ZmFrZQ=="),
        ],
    )

    result = asyncio.run(gateway.generate_video(provider, payload))
    assert result.provider_request_id == "cgt_456"
    assert result.outputs[0].url == "https://cdn.example.com/generated/finish.mp4"


def test_http_provider_gateway_volcengine_rejects_count_greater_than_one() -> None:
    gateway = HttpProviderGateway(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={}, request=request)))
    provider = _provider_record()
    payload = VideoGenerationPayload(
        provider_id=provider.provider_id,
        model="doubao-seedance-1-5-pro-251215",
        count=2,
        resolved_prompt="A cat yawns.",
    )

    async def _run() -> str:
        with pytest.raises(ValidationServiceError) as exc_info:
            await gateway.generate_video(provider, payload)
        return str(exc_info.value)

    detail = asyncio.run(_run())
    assert "count=1" in detail


def test_http_provider_gateway_volcengine_rejects_reference_images_for_seedance_1_5_pro() -> None:
    gateway = HttpProviderGateway(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={}, request=request)))
    provider = _provider_record()
    payload = VideoGenerationPayload(
        provider_id=provider.provider_id,
        model="doubao-seedance-1-5-pro-251215",
        count=1,
        image_materials=[
            VideoInputMaterial(kind="url", value="https://cdn.example.com/1.png"),
            VideoInputMaterial(kind="url", value="https://cdn.example.com/2.png"),
            VideoInputMaterial(kind="url", value="https://cdn.example.com/3.png"),
        ],
    )

    async def _run() -> str:
        with pytest.raises(ValidationServiceError) as exc_info:
            await gateway.generate_video(provider, payload)
        return str(exc_info.value)

    detail = asyncio.run(_run())
    assert "reference-image" in detail


def test_http_provider_gateway_volcengine_surfaces_failed_task_message() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, json={"id": "cgt_789"}, request=request)
        return httpx.Response(
            200,
            json={
                "id": "cgt_789",
                "status": "failed",
                "error": {"code": "InvalidParameter", "message": "duration is invalid"},
            },
            request=request,
        )

    transport = httpx.MockTransport(handler)
    gateway = HttpProviderGateway(transport=transport)
    provider = _provider_record()
    payload = VideoGenerationPayload(
        provider_id=provider.provider_id,
        model="doubao-seedance-1-5-pro-251215",
        count=1,
        resolved_prompt="A cat yawns.",
    )

    async def _run() -> str:
        with pytest.raises(UpstreamServiceError) as exc_info:
            await gateway.generate_video(provider, payload)
        return str(exc_info.value)

    detail = asyncio.run(_run())
    assert "InvalidParameter" in detail
    assert "duration is invalid" in detail
