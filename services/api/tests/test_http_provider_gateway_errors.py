from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import httpx
import pytest

from packages.provider_sdk.gateway import HttpProviderGateway
from packages.shared.contracts.generations import TextGenerationPayload
from packages.shared.contracts.providers import ProviderModelConfig, ProviderRecord
from packages.shared.enums.model_capability import ModelCapability
from services.api.app.services.errors import UpstreamServiceError


def _provider_record(*, base_url: str = "https://provider.example.com/v1") -> ProviderRecord:
    now = datetime.now(UTC)
    return ProviderRecord(
        provider_id="provider_test",
        owner_id="user_test",
        name="Test Provider",
        base_url=base_url,
        api_key="secret",
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
