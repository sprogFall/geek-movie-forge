from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import httpx
import pytest

from packages.provider_sdk.gateway import HttpProviderGateway
from packages.shared.contracts.generations import TextGenerationPayload
from packages.shared.contracts.providers import ProviderModelConfig, ProviderRecord
from packages.shared.enums.model_capability import ModelCapability
from services.api.app.services.errors import ValidationServiceError


def _provider_record(*, base_url: str) -> ProviderRecord:
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


def _payload(provider_id: str) -> TextGenerationPayload:
    return TextGenerationPayload(
        provider_id=provider_id,
        model="forge-text-v1",
        task_type="script_writing",
        source_text="hello",
        resolved_prompt="write something",
    )


def test_provider_gateway_blocks_loopback_ip_in_non_local_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("GMF_ALLOW_PRIVATE_PROVIDER_URLS", raising=False)
    monkeypatch.delenv("GMF_ALLOW_INSECURE_HTTP_PROVIDER_URLS", raising=False)

    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={}, request=request))
    gateway = HttpProviderGateway(transport=transport)
    provider = _provider_record(base_url="https://127.0.0.1:8443")
    payload = _payload(provider.provider_id)

    async def _run() -> str:
        with pytest.raises(ValidationServiceError) as exc_info:
            await gateway.generate_text(provider, payload)
        return str(exc_info.value)

    detail = asyncio.run(_run())
    assert "private/loopback" in detail


def test_provider_gateway_allows_loopback_ip_when_explicitly_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("GMF_ALLOW_PRIVATE_PROVIDER_URLS", "true")
    monkeypatch.delenv("GMF_ALLOW_INSECURE_HTTP_PROVIDER_URLS", raising=False)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"output_text": "ok"}, request=request)

    transport = httpx.MockTransport(handler)
    gateway = HttpProviderGateway(transport=transport)
    provider = _provider_record(base_url="https://127.0.0.1:8443")
    payload = _payload(provider.provider_id)

    result = asyncio.run(gateway.generate_text(provider, payload))
    assert result.output_text == "ok"


def test_provider_gateway_blocks_insecure_http_in_non_local_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("GMF_ALLOW_PRIVATE_PROVIDER_URLS", raising=False)
    monkeypatch.delenv("GMF_ALLOW_INSECURE_HTTP_PROVIDER_URLS", raising=False)

    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={}, request=request))
    gateway = HttpProviderGateway(transport=transport)
    provider = _provider_record(base_url="http://provider.example.com")
    payload = _payload(provider.provider_id)

    async def _run() -> str:
        with pytest.raises(ValidationServiceError) as exc_info:
            await gateway.generate_text(provider, payload)
        return str(exc_info.value)

    detail = asyncio.run(_run())
    assert "Insecure http" in detail


def test_provider_gateway_blocks_link_local_even_when_private_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("GMF_ALLOW_PRIVATE_PROVIDER_URLS", "true")
    monkeypatch.setenv("GMF_ALLOW_INSECURE_HTTP_PROVIDER_URLS", "true")

    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={}, request=request))
    gateway = HttpProviderGateway(transport=transport)
    provider = _provider_record(base_url="http://169.254.169.254")
    payload = _payload(provider.provider_id)

    async def _run() -> str:
        with pytest.raises(ValidationServiceError) as exc_info:
            await gateway.generate_text(provider, payload)
        return str(exc_info.value)

    detail = asyncio.run(_run())
    assert "link-local" in detail

