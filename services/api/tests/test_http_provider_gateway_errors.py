from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime

import httpx
import pytest

from packages.provider_sdk.gateway import HttpProviderGateway
from packages.shared.contracts.generations import ImageGenerationPayload, TextGenerationPayload
from packages.shared.contracts.providers import ProviderModelConfig, ProviderRecord
from packages.shared.enums.model_capability import ModelCapability
from services.api.app.services.errors import UpstreamServiceError


def _provider_record(
    *,
    base_url: str = "https://provider.example.com/v1",
    adapter_type: str = "generic_json",
) -> ProviderRecord:
    now = datetime.now(UTC)
    return ProviderRecord(
        provider_id="provider_test",
        owner_id="user_test",
        name="Test Provider",
        base_url=base_url,
        api_key="secret",
        adapter_type=adapter_type,
        models=[ProviderModelConfig(model="forge-text-v1", capabilities=[ModelCapability.TEXT])],
        created_at=now,
        updated_at=now,
    )


def test_http_provider_gateway_404_includes_url_body_and_hint() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            404,
            json={"detail": "Not Found"},
            request=request,
        )

    transport = httpx.MockTransport(handler)
    gateway = HttpProviderGateway(transport=transport)
    provider = _provider_record()
    payload = TextGenerationPayload(
        provider_id=provider.provider_id,
        model="forge-text-v1",
        task_type="script_writing",
        source_text="hello",
        resolved_prompt="write something",
    )

    async def _run() -> str:
        with pytest.raises(UpstreamServiceError) as exc_info:
            await gateway.generate_text(provider, payload)
        return str(exc_info.value)

    detail = asyncio.run(_run())
    assert "status 404" in detail
    assert "POST https://provider.example.com/v1/text/generations" in detail
    assert "Not Found" in detail
    assert "routes" in detail


def test_http_provider_gateway_invalid_json_includes_response_snippet() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text="not-json",
            headers={"Content-Type": "application/json"},
            request=request,
        )

    transport = httpx.MockTransport(handler)
    gateway = HttpProviderGateway(transport=transport)
    provider = _provider_record()
    payload = TextGenerationPayload(
        provider_id=provider.provider_id,
        model="forge-text-v1",
        task_type="script_writing",
        source_text="hello",
        resolved_prompt="write something",
    )

    async def _run() -> str:
        with pytest.raises(UpstreamServiceError) as exc_info:
            await gateway.generate_text(provider, payload)
        return str(exc_info.value)

    detail = asyncio.run(_run())
    assert "invalid JSON" in detail
    assert "POST https://provider.example.com/v1/text/generations" in detail
    assert "not-json" in detail


def test_http_provider_gateway_does_not_duplicate_when_base_url_is_full_endpoint() -> None:
    expected_url = "https://provider.example.com/v1/text/generations"

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == expected_url
        return httpx.Response(
            404,
            json={"detail": "Not Found"},
            request=request,
        )

    transport = httpx.MockTransport(handler)
    gateway = HttpProviderGateway(transport=transport)
    provider = _provider_record(base_url=expected_url)
    payload = TextGenerationPayload(
        provider_id=provider.provider_id,
        model="forge-text-v1",
        task_type="script_writing",
        source_text="hello",
        resolved_prompt="write something",
    )

    async def _run() -> str:
        with pytest.raises(UpstreamServiceError) as exc_info:
            await gateway.generate_text(provider, payload)
        return str(exc_info.value)

    detail = asyncio.run(_run())
    assert f"POST {expected_url}" in detail


def test_http_provider_gateway_uses_absolute_url_when_configured() -> None:
    expected_url = "https://alt.example.com/generate/texts"

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == expected_url
        return httpx.Response(
            404,
            json={"detail": "Not Found"},
            request=request,
        )

    transport = httpx.MockTransport(handler)
    gateway = HttpProviderGateway(transport=transport)
    provider = _provider_record()
    provider.routes.text.path = expected_url
    payload = TextGenerationPayload(
        provider_id=provider.provider_id,
        model="forge-text-v1",
        task_type="script_writing",
        source_text="hello",
        resolved_prompt="write something",
    )

    async def _run() -> str:
        with pytest.raises(UpstreamServiceError) as exc_info:
            await gateway.generate_text(provider, payload)
        return str(exc_info.value)

    detail = asyncio.run(_run())
    assert f"POST {expected_url}" in detail


def test_http_provider_gateway_generate_image_uses_default_route() -> None:
    expected_url = "https://provider.example.com/v1/image/generations"

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == expected_url
        body = json.loads(request.content.decode("utf-8"))
        assert body["model"] == "forge-image-v1"
        assert body["count"] == 1
        assert body["prompt"] == "Render a dramatic poster"
        return httpx.Response(
            200,
            json={
                "provider_request_id": "img_123",
                "outputs": [{"index": 0, "url": "https://cdn.example.com/generated/poster.png"}],
            },
            request=request,
        )

    transport = httpx.MockTransport(handler)
    gateway = HttpProviderGateway(transport=transport)
    provider = _provider_record()
    payload = ImageGenerationPayload(
        provider_id=provider.provider_id,
        model="forge-image-v1",
        count=1,
        resolved_prompt="Render a dramatic poster",
    )

    result = asyncio.run(gateway.generate_image(provider, payload))
    assert result.provider_request_id == "img_123"
    assert result.outputs[0].url == "https://cdn.example.com/generated/poster.png"


def test_http_provider_gateway_modelscope_image_uses_async_flow() -> None:
    requests_seen: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests_seen.append((request.method, str(request.url)))
        if request.method == "POST":
            assert str(request.url) == "https://api-inference.modelscope.cn/v1/images/generations"
            assert request.headers["X-ModelScope-Async-Mode"] == "true"
            body = json.loads(request.content.decode("utf-8"))
            assert body["model"] == "Qwen/Qwen-Image-2512"
            return httpx.Response(
                200,
                json={"task_id": "task_123", "request_id": "req_123"},
                request=request,
            )

        assert str(request.url) == "https://api-inference.modelscope.cn/v1/tasks/task_123"
        assert request.headers["X-ModelScope-Task-Type"] == "image_generation"
        return httpx.Response(
            200,
            json={
                "task_status": "SUCCEED",
                "output_images": ["https://cdn.example.com/generated/modelscope-image.png"],
            },
            request=request,
        )

    transport = httpx.MockTransport(handler)
    gateway = HttpProviderGateway(transport=transport)
    provider = _provider_record(
        base_url="https://api-inference.modelscope.cn",
        adapter_type="modelscope",
    )
    provider.routes.image.path = "/v1/images/generations"
    payload = ImageGenerationPayload(
        provider_id=provider.provider_id,
        model="Qwen/Qwen-Image-2512",
        count=1,
        resolved_prompt="A golden cat",
    )

    result = asyncio.run(gateway.generate_image(provider, payload))
    assert requests_seen == [
        ("POST", "https://api-inference.modelscope.cn/v1/images/generations"),
        ("GET", "https://api-inference.modelscope.cn/v1/tasks/task_123"),
    ]
    assert result.provider_request_id == "task_123"
    assert result.outputs[0].url == "https://cdn.example.com/generated/modelscope-image.png"


def test_http_provider_gateway_uses_openai_compatible_chat_payload_when_configured() -> None:
    expected_url = "https://provider.example.com/v1/chat/completions"

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == expected_url
        body = json.loads(request.content.decode("utf-8"))
        assert body["model"] == "moonshotai/Kimi-K2.5"
        assert body["stream"] is False
        assert body["messages"][0] == {"role": "system", "content": "Write a trailer"}
        assert body["messages"][1]["role"] == "user"
        assert "Task type: script_writing" in body["messages"][1]["content"]
        assert "Source text:\nA pilot is stranded on Mars." in body["messages"][1]["content"]
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl_123",
                "choices": [{"message": {"content": "Opening shot: red dust and silence."}}],
                "usage": {"total_tokens": 42},
            },
            request=request,
        )

    transport = httpx.MockTransport(handler)
    gateway = HttpProviderGateway(transport=transport)
    provider = _provider_record()
    provider.routes.text.path = expected_url
    payload = TextGenerationPayload(
        provider_id=provider.provider_id,
        model="moonshotai/Kimi-K2.5",
        task_type="script_writing",
        source_text="A pilot is stranded on Mars.",
        resolved_prompt="Write a trailer",
    )

    result = asyncio.run(gateway.generate_text(provider, payload))
    assert result.provider_request_id == "chatcmpl_123"
    assert result.output_text == "Opening shot: red dust and silence."
    assert result.metadata["usage"]["total_tokens"] == 42
